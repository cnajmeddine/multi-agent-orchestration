# workflows.py - CRUD endpoints for workflows
# This file defines the API endpoints for managing workflows.

from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from typing import List, Optional
import logging

from ..models import (
    WorkflowDefinition, WorkflowCreateRequest, WorkflowExecutionRequest,
    WorkflowExecution, WorkflowStatus
)
from ..workflow_registry import WorkflowRegistry
from ..workflow_engine import WorkflowEngine

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/workflows", tags=["workflows"])

# Dependencies
def get_registry():
    return WorkflowRegistry()

def get_engine():
    return WorkflowEngine()

@router.post("/", response_model=WorkflowDefinition)
async def create_workflow(
    request: WorkflowCreateRequest,
    registry: WorkflowRegistry = Depends(get_registry)
):
    """Create a new workflow definition."""
    try:
        workflow = WorkflowDefinition(
            name=request.name,
            description=request.description,
            steps=request.steps,
            global_timeout=request.global_timeout
        )
        
        success = await registry.store_workflow_definition(workflow)
        if not success:
            raise HTTPException(status_code=500, detail="Failed to store workflow")
        
        logger.info(f"Created workflow {workflow.workflow_id}: {workflow.name}")
        return workflow
        
    except Exception as e:
        logger.error(f"Failed to create workflow: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/", response_model=List[WorkflowDefinition])
async def list_workflows(
    registry: WorkflowRegistry = Depends(get_registry)
):
    """List all workflow definitions."""
    try:
        workflows = await registry.list_workflow_definitions()
        return workflows
        
    except Exception as e:
        logger.error(f"Failed to list workflows: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{workflow_id}", response_model=WorkflowDefinition)
async def get_workflow(
    workflow_id: str,
    registry: WorkflowRegistry = Depends(get_registry)
):
    """Get specific workflow definition."""
    try:
        workflow = await registry.get_workflow_definition(workflow_id)
        if not workflow:
            raise HTTPException(status_code=404, detail="Workflow not found")
        
        return workflow
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get workflow {workflow_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/{workflow_id}")
async def delete_workflow(
    workflow_id: str,
    registry: WorkflowRegistry = Depends(get_registry)
):
    """Delete a workflow definition."""
    try:
        success = await registry.delete_workflow_definition(workflow_id)
        if not success:
            raise HTTPException(status_code=404, detail="Workflow not found")
        
        return {"message": f"Workflow {workflow_id} deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete workflow {workflow_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{workflow_id}/execute", response_model=WorkflowExecution)
async def execute_workflow(
    workflow_id: str,
    request: WorkflowExecutionRequest,
    background_tasks: BackgroundTasks,
    registry: WorkflowRegistry = Depends(get_registry),
    engine: WorkflowEngine = Depends(get_engine)
):
    """Start workflow execution."""
    try:
        # Get workflow definition
        workflow_def = await registry.get_workflow_definition(workflow_id)
        if not workflow_def:
            raise HTTPException(status_code=404, detail="Workflow not found")
        
        # Create execution using workflow_id from path and input_data from request
        execution = WorkflowExecution(
            workflow_id=workflow_id,  # Use path parameter
            input_data=request.input_data,  # Use request body
            status=WorkflowStatus.PENDING
        )
        
        # Store initial execution state
        await registry.store_workflow_execution(execution)
        
        # Start execution in background
        async def execute_and_store():
            try:
                # Execute workflow
                updated_execution = await engine.execute_workflow(workflow_def, execution)
                
                # Store final state
                await registry.store_workflow_execution(updated_execution)
                
                # Update status indexes
                await registry.update_execution_status(
                    execution.execution_id, 
                    WorkflowStatus.PENDING.value,
                    updated_execution.status.value
                )
                
            except Exception as e:
                logger.error(f"Background execution failed for {execution.execution_id}: {str(e)}")
                # Store error state
                execution.status = WorkflowStatus.FAILED
                execution.error_message = str(e)
                await registry.store_workflow_execution(execution)
        
        background_tasks.add_task(execute_and_store)
        
        logger.info(f"Started workflow execution {execution.execution_id}")
        return execution
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to execute workflow {workflow_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{workflow_id}/executions", response_model=List[WorkflowExecution])
async def list_workflow_executions(
    workflow_id: str,
    status: Optional[str] = None,
    registry: WorkflowRegistry = Depends(get_registry)
):
    """List executions for a specific workflow."""
    try:
        executions = await registry.list_workflow_executions(
            workflow_id=workflow_id, 
            status=status
        )
        return executions
        
    except Exception as e:
        logger.error(f"Failed to list executions for workflow {workflow_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))