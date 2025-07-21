# workflow_engine.py - Core execution engine for workflows
# This file contains the logic for executing workflows step by step.

import asyncio
import logging
import httpx
from typing import Dict, List, Optional, Any, Set
from datetime import datetime, timedelta

from .models import (
    WorkflowDefinition, WorkflowExecution, StepExecution, 
    WorkflowStatus, StepStatus, WorkflowStep
)
from .config import settings

logger = logging.getLogger(__name__)

class WorkflowEngine:
    def __init__(self):
        self.running_executions: Dict[str, asyncio.Task] = {}
        self.agent_client = httpx.AsyncClient(base_url=settings.agent_service_url)
    
    async def execute_workflow(self, workflow_def: WorkflowDefinition, 
                             execution: WorkflowExecution) -> WorkflowExecution:
        """Execute a workflow definition."""
        logger.info(f"Starting workflow execution {execution.execution_id}")
        
        try:
            # Update execution status
            execution.status = WorkflowStatus.RUNNING
            execution.start_time = datetime.utcnow()
            
            # Initialize step executions
            execution.step_executions = [
                StepExecution(
                    step_id=step.step_id,
                    execution_id=execution.execution_id
                ) for step in workflow_def.steps
            ]
            
            # Set initial context with input data
            execution.context.update(execution.input_data)
            
            # Execute steps using topological sort
            completed_steps = set()
            max_iterations = len(workflow_def.steps) * 2  # Prevent infinite loops
            iteration = 0
            
            while len(completed_steps) < len(workflow_def.steps) and iteration < max_iterations:
                iteration += 1
                progress_made = False
                
                for step in workflow_def.steps:
                    if step.step_id in completed_steps:
                        continue
                    
                    # Check if dependencies are met
                    if self._dependencies_satisfied(step, completed_steps):
                        step_execution = self._get_step_execution(execution, step.step_id)
                        
                        if step_execution.status == StepStatus.PENDING:
                            # Execute step
                            await self._execute_step(workflow_def, execution, step, step_execution)
                            
                            if step_execution.status in [StepStatus.COMPLETED, StepStatus.FAILED, StepStatus.SKIPPED]:
                                completed_steps.add(step.step_id)
                                progress_made = True
                                
                                # If step failed and no retry, fail workflow
                                if step_execution.status == StepStatus.FAILED and step_execution.retry_attempt >= step.retry_count:
                                    execution.status = WorkflowStatus.FAILED
                                    execution.error_message = f"Step {step.name} failed: {step_execution.error_message}"
                                    break
                
                if execution.status == WorkflowStatus.FAILED:
                    break
                    
                if not progress_made:
                    # Check for circular dependencies
                    logger.error(f"Workflow {execution.execution_id} appears to have circular dependencies")
                    execution.status = WorkflowStatus.FAILED
                    execution.error_message = "Circular dependency detected in workflow"
                    break
            
            # Finalize execution
            if execution.status == WorkflowStatus.RUNNING:
                execution.status = WorkflowStatus.COMPLETED
            
            execution.end_time = datetime.utcnow()
            logger.info(f"Workflow execution {execution.execution_id} completed with status: {execution.status}")
            
        except Exception as e:
            logger.error(f"Workflow execution {execution.execution_id} failed: {str(e)}")
            execution.status = WorkflowStatus.FAILED
            execution.error_message = str(e)
            execution.end_time = datetime.utcnow()
        
        return execution
    
    async def _execute_step(self, workflow_def: WorkflowDefinition, 
                          execution: WorkflowExecution, step: WorkflowStep, 
                          step_execution: StepExecution):
        """Execute a single workflow step."""
        logger.info(f"Executing step {step.name} in workflow {execution.execution_id}")
        
        try:
            step_execution.status = StepStatus.RUNNING
            step_execution.start_time = datetime.utcnow()
            
            # Check condition if specified
            if step.condition and not self._evaluate_condition(step.condition, execution.context):
                logger.info(f"Step {step.name} skipped due to condition: {step.condition}")
                step_execution.status = StepStatus.SKIPPED
                step_execution.end_time = datetime.utcnow()
                return
            
            # Prepare input data using input mapping
            input_data = self._map_step_input(step, execution.context)
            step_execution.input_data = input_data
            
            # Execute agent task
            agent_response = await self._call_agent(step.agent_type, input_data, step.timeout)
            
            if agent_response.get("success"):
                step_execution.status = StepStatus.COMPLETED
                step_execution.output_data = agent_response.get("output_data", {})
                step_execution.agent_id = agent_response.get("agent_id")
                
                # Update workflow context using output mapping
                self._map_step_output(step, step_execution.output_data, execution.context)
                
                logger.info(f"Step {step.name} completed successfully")
            else:
                step_execution.status = StepStatus.FAILED
                step_execution.error_message = agent_response.get("error_message", "Unknown error")
                
                # Retry logic
                if step_execution.retry_attempt < step.retry_count:
                    step_execution.retry_attempt += 1
                    step_execution.status = StepStatus.PENDING
                    logger.info(f"Retrying step {step.name} (attempt {step_execution.retry_attempt + 1})")
                    await asyncio.sleep(2 ** step_execution.retry_attempt)  # Exponential backoff
                else:
                    logger.error(f"Step {step.name} failed after {step.retry_count} retries")
            
        except Exception as e:
            logger.error(f"Step {step.name} execution failed: {str(e)}")
            step_execution.status = StepStatus.FAILED
            step_execution.error_message = str(e)
        
        finally:
            step_execution.end_time = datetime.utcnow()
    
    async def _call_agent(self, agent_type: str, input_data: Dict[str, Any], timeout: int) -> Dict[str, Any]:
        """Call the agent service to execute a task."""
        try:
            payload = {
                "agent_type": agent_type,
                "input_data": input_data,
                "timeout": timeout
            }
            
            response = await self.agent_client.post("/agents/execute", json=payload, timeout=timeout + 10)
            response.raise_for_status()
            
            return response.json()
            
        except httpx.TimeoutException:
            logger.error(f"Agent call timed out for type {agent_type}")
            return {"success": False, "error_message": "Agent call timed out"}
        except httpx.HTTPStatusError as e:
            logger.error(f"Agent call failed with status {e.response.status_code}: {e.response.text}")
            return {"success": False, "error_message": f"HTTP {e.response.status_code}: {e.response.text}"}
        except Exception as e:
            logger.error(f"Agent call failed: {str(e)}")
            return {"success": False, "error_message": str(e)}
    
    def _dependencies_satisfied(self, step: WorkflowStep, completed_steps: Set[str]) -> bool:
        """Check if all dependencies for a step are satisfied."""
        return all(dep_id in completed_steps for dep_id in step.depends_on)
    
    def _get_step_execution(self, execution: WorkflowExecution, step_id: str) -> StepExecution:
        """Get step execution by step_id."""
        for step_exec in execution.step_executions:
            if step_exec.step_id == step_id:
                return step_exec
        raise ValueError(f"Step execution not found for step_id: {step_id}")
    
    def _map_step_input(self, step: WorkflowStep, context: Dict[str, Any]) -> Dict[str, Any]:
        """Map workflow context to step input using input_mapping."""
        mapped_input = {}
        
        for step_input_key, context_key in step.input_mapping.items():
            if context_key in context:
                mapped_input[step_input_key] = context[context_key]
            else:
                logger.warning(f"Context key '{context_key}' not found for step input '{step_input_key}'")
        
        return mapped_input
    
    def _map_step_output(self, step: WorkflowStep, step_output: Dict[str, Any], context: Dict[str, Any]):
        """Map step output to workflow context using output_mapping."""
        for step_output_key, context_key in step.output_mapping.items():
            if step_output_key in step_output:
                context[context_key] = step_output[step_output_key]
            else:
                logger.warning(f"Step output key '{step_output_key}' not found for context key '{context_key}'")
    
    def _evaluate_condition(self, condition: str, context: Dict[str, Any]) -> bool:
        """Evaluate a simple condition against the workflow context."""
        # Simple condition evaluation (expand as needed)
        # Format: "key operator value" e.g., "sentiment == positive"
        try:
            parts = condition.split()
            if len(parts) != 3:
                logger.warning(f"Invalid condition format: {condition}")
                return True
            
            key, operator, value = parts
            context_value = context.get(key)
            
            if context_value is None:
                return False
            
            # Convert value to appropriate type
            if value.lower() == 'true':
                value = True
            elif value.lower() == 'false':
                value = False
            elif value.isdigit():
                value = int(value)
            elif value.replace('.', '').isdigit():
                value = float(value)
            
            # Evaluate condition
            if operator == "==":
                return context_value == value
            elif operator == "!=":
                return context_value != value
            elif operator == ">":
                return float(context_value) > float(value)
            elif operator == "<":
                return float(context_value) < float(value)
            elif operator == ">=":
                return float(context_value) >= float(value)
            elif operator == "<=":
                return float(context_value) <= float(value)
            else:
                logger.warning(f"Unknown operator in condition: {operator}")
                return True
                
        except Exception as e:
            logger.error(f"Error evaluating condition '{condition}': {str(e)}")
            return True  # Default to true on error
    
    async def start_workflow_execution(self, workflow_def: WorkflowDefinition, 
                                     execution: WorkflowExecution):
        """Start workflow execution in background."""
        task = asyncio.create_task(self.execute_workflow(workflow_def, execution))
        self.running_executions[execution.execution_id] = task
        return task
    
    async def cancel_workflow_execution(self, execution_id: str) -> bool:
        """Cancel a running workflow execution."""
        if execution_id in self.running_executions:
            task = self.running_executions[execution_id]
            task.cancel()
            del self.running_executions[execution_id]
            logger.info(f"Cancelled workflow execution {execution_id}")
            return True
        return False
    
    def get_running_executions(self) -> List[str]:
        """Get list of currently running execution IDs."""
        return list(self.running_executions.keys())
    
    async def cleanup_completed_executions(self):
        """Clean up completed execution tasks."""
        completed_executions = []
        for execution_id, task in self.running_executions.items():
            if task.done():
                completed_executions.append(execution_id)
        
        for execution_id in completed_executions:
            del self.running_executions[execution_id]
        
        if completed_executions:
            logger.info(f"Cleaned up {len(completed_executions)} completed execution tasks")