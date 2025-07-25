# services/workflow_service/event_publisher.py
# Event publishing for workflow service

import asyncio
import httpx
import logging
from typing import Dict, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

class WorkflowEventPublisher:
    """Publishes workflow events to communication and monitoring services."""
    
    def __init__(self):
        self.communication_url = "http://localhost:8004"
        self.monitoring_url = "http://localhost:8003"
        self.http_client = httpx.AsyncClient(timeout=5.0)
    
    async def publish_workflow_started(self, execution_id: str, workflow_id: str, 
                                     workflow_name: str, step_count: int):
        """Publish workflow started event."""
        event_data = {
            "event_type": "workflow.started",
            "source_service": "workflow-service",
            "source_id": execution_id,
            "priority": "medium",
            "payload": {
                "workflow_id": workflow_id,
                "workflow_name": workflow_name,
                "step_count": step_count,
                "execution_id": execution_id
            },
            "metadata": {
                "execution_id": execution_id,
                "workflow_id": workflow_id,
                "timestamp": datetime.utcnow().isoformat()
            }
        }
        
        await self._send_to_communication(event_data)
        await self._send_counter_to_monitoring("workflows_started", 1)
    
    async def publish_workflow_completed(self, execution_id: str, workflow_id: str,
                                       duration_seconds: float, steps_completed: int):
        """Publish workflow completed event."""
        event_data = {
            "event_type": "workflow.completed",
            "source_service": "workflow-service",
            "source_id": execution_id,
            "priority": "medium",
            "payload": {
                "workflow_id": workflow_id,
                "execution_id": execution_id,
                "duration_seconds": duration_seconds,
                "steps_completed": steps_completed
            },
            "metadata": {
                "execution_id": execution_id,
                "workflow_id": workflow_id,
                "timestamp": datetime.utcnow().isoformat()
            }
        }
        
        await self._send_to_communication(event_data)
        await self._send_counter_to_monitoring("workflows_completed", 1)
        await self._send_metric_to_monitoring("workflow_execution_time", duration_seconds, 
                                            {"workflow_id": workflow_id})
    
    async def publish_workflow_failed(self, execution_id: str, workflow_id: str,
                                    error_message: str, failed_step: str = None):
        """Publish workflow failed event."""
        event_data = {
            "event_type": "workflow.failed",
            "source_service": "workflow-service", 
            "source_id": execution_id,
            "priority": "high",
            "payload": {
                "workflow_id": workflow_id,
                "execution_id": execution_id,
                "error_message": error_message,
                "failed_step": failed_step
            },
            "metadata": {
                "execution_id": execution_id,
                "workflow_id": workflow_id,
                "timestamp": datetime.utcnow().isoformat()
            }
        }
        
        await self._send_to_communication(event_data)
        await self._send_counter_to_monitoring("workflows_failed", 1)
    
    async def publish_workflow_paused(self, execution_id: str, workflow_id: str):
        """Publish workflow paused event."""
        event_data = {
            "event_type": "workflow.paused",
            "source_service": "workflow-service",
            "source_id": execution_id,
            "priority": "medium",
            "payload": {
                "workflow_id": workflow_id,
                "execution_id": execution_id
            },
            "metadata": {
                "execution_id": execution_id,
                "workflow_id": workflow_id,
                "timestamp": datetime.utcnow().isoformat()
            }
        }
        
        await self._send_to_communication(event_data)
    
    async def publish_workflow_resumed(self, execution_id: str, workflow_id: str):
        """Publish workflow resumed event."""
        event_data = {
            "event_type": "workflow.resumed",
            "source_service": "workflow-service",
            "source_id": execution_id,
            "priority": "medium",
            "payload": {
                "workflow_id": workflow_id,
                "execution_id": execution_id
            },
            "metadata": {
                "execution_id": execution_id,
                "workflow_id": workflow_id,
                "timestamp": datetime.utcnow().isoformat()
            }
        }
        
        await self._send_to_communication(event_data)
    
    async def publish_step_started(self, execution_id: str, step_id: str, 
                                 step_name: str, agent_type: str):
        """Publish step started event."""
        event_data = {
            "event_type": "step.started",
            "source_service": "workflow-service",
            "source_id": f"{execution_id}:{step_id}",
            "priority": "low",
            "payload": {
                "execution_id": execution_id,
                "step_id": step_id,
                "step_name": step_name,
                "agent_type": agent_type
            },
            "metadata": {
                "execution_id": execution_id,
                "step_id": step_id,
                "timestamp": datetime.utcnow().isoformat()
            }
        }
        
        await self._send_to_communication(event_data)
        await self._send_counter_to_monitoring("steps_started", 1)
    
    async def publish_step_completed(self, execution_id: str, step_id: str,
                                   execution_time: float, agent_id: str = None):
        """Publish step completed event."""
        event_data = {
            "event_type": "step.completed",
            "source_service": "workflow-service",
            "source_id": f"{execution_id}:{step_id}",
            "priority": "low",
            "payload": {
                "execution_id": execution_id,
                "step_id": step_id,
                "execution_time": execution_time,
                "agent_id": agent_id
            },
            "metadata": {
                "execution_id": execution_id,
                "step_id": step_id,
                "timestamp": datetime.utcnow().isoformat()
            }
        }
        
        await self._send_to_communication(event_data)
        await self._send_counter_to_monitoring("steps_completed", 1)
        await self._send_metric_to_monitoring("step_execution_time", execution_time,
                                            {"step_id": step_id})
    
    async def publish_step_failed(self, execution_id: str, step_id: str,
                                execution_time: float, error_message: str,
                                retry_attempt: int = 0):
        """Publish step failed event."""
        event_data = {
            "event_type": "step.failed",
            "source_service": "workflow-service",
            "source_id": f"{execution_id}:{step_id}",
            "priority": "high",
            "payload": {
                "execution_id": execution_id,
                "step_id": step_id,
                "execution_time": execution_time,
                "error_message": error_message,
                "retry_attempt": retry_attempt
            },
            "metadata": {
                "execution_id": execution_id,
                "step_id": step_id,
                "timestamp": datetime.utcnow().isoformat()
            }
        }
        
        await self._send_to_communication(event_data)
        await self._send_counter_to_monitoring("steps_failed", 1)
    
    async def _send_to_communication(self, event_data: Dict[str, Any]):
        """Send event to communication service."""
        try:
            response = await self.http_client.post(
                f"{self.communication_url}/events/publish",
                json=event_data
            )
            response.raise_for_status()
            
        except Exception as e:
            logger.warning(f"Failed to send event to communication service: {str(e)}")
    
    async def _send_metric_to_monitoring(self, metric_name: str, value: float,
                                       labels: Dict[str, str] = None):
        """Send metric to monitoring service."""
        try:
            params = {"metric_name": metric_name, "value": value}
            if labels:
                params["labels"] = labels
            
            response = await self.http_client.post(
                f"{self.monitoring_url}/metrics/record",
                params=params
            )
            response.raise_for_status()
            
        except Exception as e:
            logger.warning(f"Failed to send metric to monitoring: {str(e)}")
    
    async def _send_counter_to_monitoring(self, counter_name: str, increment: int = 1):
        """Send counter increment to monitoring service."""
        try:
            response = await self.http_client.post(
                f"{self.monitoring_url}/counters/increment",
                params={"counter_name": counter_name, "increment": increment}
            )
            response.raise_for_status()
            
        except Exception as e:
            logger.warning(f"Failed to send counter to monitoring: {str(e)}")
    
    async def close(self):
        """Close HTTP client."""
        await self.http_client.aclose()

# Global event publisher
event_publisher = WorkflowEventPublisher()

# Integration with Enhanced Workflow Engine
# Add this to your enhanced_workflow_engine.py:

class EventIntegratedWorkflowEngine(EnhancedWorkflowEngine):
    """Workflow engine with full event integration."""
    
    def __init__(self):
        super().__init__()
        self.event_publisher = WorkflowEventPublisher()
    
    async def execute_workflow(self, workflow_def: WorkflowDefinition, 
                             execution: WorkflowExecution) -> WorkflowExecution:
        """Execute workflow with event publishing."""
        
        # Publish workflow started
        await self.event_publisher.publish_workflow_started(
            execution.execution_id,
            workflow_def.workflow_id,
            workflow_def.name,
            len(workflow_def.steps)
        )
        
        try:
            result = await super().execute_workflow(workflow_def, execution)
            
            # Publish completion events
            if result.status == WorkflowStatus.COMPLETED:
                duration = (result.end_time - result.start_time).total_seconds() if result.end_time and result.start_time else 0
                steps_completed = len([s for s in result.step_executions if s.status == StepStatus.COMPLETED])
                
                await self.event_publisher.publish_workflow_completed(
                    execution.execution_id,
                    workflow_def.workflow_id,
                    duration,
                    steps_completed
                )
                
            elif result.status == WorkflowStatus.FAILED:
                failed_step = next((s.step_id for s in result.step_executions if s.status == StepStatus.FAILED), None)
                
                await self.event_publisher.publish_workflow_failed(
                    execution.execution_id,
                    workflow_def.workflow_id,
                    result.error_message or "Unknown error",
                    failed_step
                )
            
            return result
            
        except Exception as e:
            await self.event_publisher.publish_workflow_failed(
                execution.execution_id,
                workflow_def.workflow_id,
                str(e)
            )
            raise
    
    async def pause_workflow(self, execution_id: str) -> bool:
        """Pause workflow with event publishing."""
        result = await super().pause_workflow(execution_id)
        
        if result:
            # Get workflow_id for event
            from .workflow_registry import WorkflowRegistry
            registry = WorkflowRegistry()
            execution = await registry.get_workflow_execution(execution_id)
            
            if execution:
                await self.event_publisher.publish_workflow_paused(
                    execution_id, execution.workflow_id
                )
        
        return result
    
    async def resume_workflow(self, execution_id: str) -> bool:
        """Resume workflow with event publishing."""
        result = await super().resume_workflow(execution_id)
        
        if result:
            # Get workflow_id for event
            from .workflow_registry import WorkflowRegistry
            registry = WorkflowRegistry()
            execution = await registry.get_workflow_execution(execution_id)
            
            if execution:
                await self.event_publisher.publish_workflow_resumed(
                    execution_id, execution.workflow_id
                )
        
        return result
    
    async def _execute_step_enhanced(self, workflow_def: WorkflowDefinition,
                                   execution: WorkflowExecution, step: WorkflowStep,
                                   step_execution: StepExecution):
        """Execute step with event publishing."""
        
        # Publish step started
        await self.event_publisher.publish_step_started(
            execution.execution_id,
            step.step_id,
            step.name,
            step.agent_type
        )
        
        start_time = asyncio.get_event_loop().time()
        
        try:
            # Execute step (call parent method)
            await super()._execute_step_enhanced(workflow_def, execution, step, step_execution)
            
            execution_time = asyncio.get_event_loop().time() - start_time
            
            # Publish step events based on result
            if step_execution.status == StepStatus.COMPLETED:
                await self.event_publisher.publish_step_completed(
                    execution.execution_id,
                    step.step_id,
                    execution_time,
                    step_execution.agent_id
                )
                
            elif step_execution.status == StepStatus.FAILED:
                await self.event_publisher.publish_step_failed(
                    execution.execution_id,
                    step.step_id,
                    execution_time,
                    step_execution.error_message or "Unknown error",
                    step_execution.retry_attempt
                )
            
        except Exception as e:
            execution_time = asyncio.get_event_loop().time() - start_time
            
            await self.event_publisher.publish_step_failed(
                execution.execution_id,
                step.step_id,
                execution_time,
                str(e)
            )
            raise

event_publisher = WorkflowEventPublisher()