# workflow_registry.py - Redis-based workflow storage
# This file contains logic for storing and retrieving workflows using Redis.

import redis
import json
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime

from .models import WorkflowDefinition, WorkflowExecution
from .config import settings

logger = logging.getLogger(__name__)

class WorkflowRegistry:
    def __init__(self):
        self.redis_client = redis.Redis(
            host=settings.redis_host,
            port=settings.redis_port,
            db=settings.redis_db,
            password=settings.redis_password,
            decode_responses=True
        )
    
    # Workflow Definitions
    async def store_workflow_definition(self, workflow: WorkflowDefinition) -> bool:
        """Store workflow definition in Redis."""
        try:
            workflow_key = f"workflow:def:{workflow.workflow_id}"
            workflow_data = workflow.dict()
            
            # Convert datetime to ISO string
            workflow_data['created_at'] = workflow_data['created_at'].isoformat()
            
            # Store as JSON
            self.redis_client.set(workflow_key, json.dumps(workflow_data))
            
            # Add to workflow index
            self.redis_client.sadd("workflows:all", workflow.workflow_id)
            
            # Index by name for quick lookup
            self.redis_client.hset("workflows:by_name", workflow.name, workflow.workflow_id)
            
            logger.info(f"Stored workflow definition {workflow.workflow_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to store workflow {workflow.workflow_id}: {str(e)}")
            return False
    
    async def get_workflow_definition(self, workflow_id: str) -> Optional[WorkflowDefinition]:
        """Retrieve workflow definition from Redis."""
        try:
            workflow_key = f"workflow:def:{workflow_id}"
            workflow_data = self.redis_client.get(workflow_key)
            
            if not workflow_data:
                return None
            
            parsed_data = json.loads(workflow_data)
            parsed_data['created_at'] = datetime.fromisoformat(parsed_data['created_at'])
            
            return WorkflowDefinition(**parsed_data)
            
        except Exception as e:
            logger.error(f"Failed to get workflow {workflow_id}: {str(e)}")
            return None
    
    async def list_workflow_definitions(self) -> List[WorkflowDefinition]:
        """List all workflow definitions."""
        try:
            workflow_ids = self.redis_client.smembers("workflows:all")
            workflows = []
            
            for workflow_id in workflow_ids:
                workflow = await self.get_workflow_definition(workflow_id)
                if workflow:
                    workflows.append(workflow)
            
            return workflows
            
        except Exception as e:
            logger.error(f"Failed to list workflows: {str(e)}")
            return []
    
    async def delete_workflow_definition(self, workflow_id: str) -> bool:
        """Delete workflow definition."""
        try:
            workflow = await self.get_workflow_definition(workflow_id)
            if not workflow:
                return False
            
            # Remove from Redis
            workflow_key = f"workflow:def:{workflow_id}"
            self.redis_client.delete(workflow_key)
            self.redis_client.srem("workflows:all", workflow_id)
            self.redis_client.hdel("workflows:by_name", workflow.name)
            
            logger.info(f"Deleted workflow definition {workflow_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete workflow {workflow_id}: {str(e)}")
            return False
    
    # Workflow Executions
    async def store_workflow_execution(self, execution: WorkflowExecution) -> bool:
        """Store workflow execution state in Redis."""
        try:
            execution_key = f"workflow:exec:{execution.execution_id}"
            execution_data = execution.dict()
            
            # Convert datetimes to ISO strings
            for key in ['start_time', 'end_time']:
                if execution_data[key]:
                    execution_data[key] = execution_data[key].isoformat()
            
            # Convert step execution datetimes
            for step_exec in execution_data['step_executions']:
                for key in ['start_time', 'end_time']:
                    if step_exec[key]:
                        step_exec[key] = step_exec[key].isoformat()
            
            # Store as JSON
            self.redis_client.set(execution_key, json.dumps(execution_data))
            
            # Add to execution indexes
            self.redis_client.sadd("executions:all", execution.execution_id)
            self.redis_client.sadd(f"executions:workflow:{execution.workflow_id}", execution.execution_id)
            self.redis_client.sadd(f"executions:status:{execution.status.value}", execution.execution_id)
            
            # Set expiration (keep executions for 7 days)
            self.redis_client.expire(execution_key, 7 * 24 * 3600)
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to store execution {execution.execution_id}: {str(e)}")
            return False
    
    async def get_workflow_execution(self, execution_id: str) -> Optional[WorkflowExecution]:
        """Retrieve workflow execution from Redis."""
        try:
            execution_key = f"workflow:exec:{execution_id}"
            execution_data = self.redis_client.get(execution_key)
            
            if not execution_data:
                return None
            
            parsed_data = json.loads(execution_data)
            
            # Convert datetime strings back
            for key in ['start_time', 'end_time']:
                if parsed_data[key]:
                    parsed_data[key] = datetime.fromisoformat(parsed_data[key])
            
            # Convert step execution datetimes
            for step_exec in parsed_data['step_executions']:
                for key in ['start_time', 'end_time']:
                    if step_exec[key]:
                        step_exec[key] = datetime.fromisoformat(step_exec[key])
            
            return WorkflowExecution(**parsed_data)
            
        except Exception as e:
            logger.error(f"Failed to get execution {execution_id}: {str(e)}")
            return None
    
    async def list_workflow_executions(self, workflow_id: Optional[str] = None, 
                                     status: Optional[str] = None) -> List[WorkflowExecution]:
        """List workflow executions with optional filtering."""
        try:
            if workflow_id:
                execution_ids = self.redis_client.smembers(f"executions:workflow:{workflow_id}")
            elif status:
                execution_ids = self.redis_client.smembers(f"executions:status:{status}")
            else:
                execution_ids = self.redis_client.smembers("executions:all")
            
            executions = []
            for execution_id in execution_ids:
                execution = await self.get_workflow_execution(execution_id)
                if execution:
                    executions.append(execution)
            
            # Sort by start time (newest first)
            executions.sort(key=lambda x: x.start_time or datetime.min, reverse=True)
            return executions
            
        except Exception as e:
            logger.error(f"Failed to list executions: {str(e)}")
            return []
    
    async def update_execution_status(self, execution_id: str, 
                                    old_status: str, new_status: str) -> bool:
        """Update execution status indexes."""
        try:
            self.redis_client.srem(f"executions:status:{old_status}", execution_id)
            self.redis_client.sadd(f"executions:status:{new_status}", execution_id)
            return True
        except Exception as e:
            logger.error(f"Failed to update execution status indexes: {str(e)}")
            return False