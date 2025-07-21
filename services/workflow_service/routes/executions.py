# executions.py - Start/monitor workflow executions
# This file defines the API endpoints for starting and monitoring workflow executions.

from fastapi import APIRouter, HTTPException, Depends
from typing import List, Optional
import logging

from ..models import WorkflowExecution, WorkflowStatus
from ..workflow_registry import WorkflowRegistry
from ..workflow_engine import WorkflowEngine

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/executions", tags=["executions"])

# Dependencies
def get_registry():
    return WorkflowRegistry()

def get_engine():
    return WorkflowEngine()

@router.get("/", response_model=List[WorkflowExecution])
async def list_executions(
    status: Optional[str] = None,
    limit: int = 50,
    registry: WorkflowRegistry = Depends(get_registry)
):
    """List workflow executions with optional filtering."""
    try:
        executions = await registry.list_workflow_executions(status=status)
        return executions[:limit]  # Simple pagination
        
    except Exception as e:
        logger.error(f"Failed to list executions: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{execution_id}", response_model=WorkflowExecution)
async def get_execution(
    execution_id: str,
    registry: WorkflowRegistry = Depends(get_registry)
):
    """Get specific workflow execution details."""
    try:
        execution = await registry.get_workflow_execution(execution_id)
        if not execution:
            raise HTTPException(status_code=404, detail="Execution not found")
        
        return execution
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get execution {execution_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{execution_id}/cancel")
async def cancel_execution(
    execution_id: str,
    registry: WorkflowRegistry = Depends(get_registry),
    engine: WorkflowEngine = Depends(get_engine)
):
    """Cancel a running workflow execution."""
    try:
        # Get current execution
        execution = await registry.get_workflow_execution(execution_id)
        if not execution:
            raise HTTPException(status_code=404, detail="Execution not found")
        
        if execution.status not in [WorkflowStatus.PENDING, WorkflowStatus.RUNNING]:
            raise HTTPException(
                status_code=400, 
                detail=f"Cannot cancel execution with status: {execution.status}"
            )
        
        # Cancel in engine
        cancelled = await engine.cancel_workflow_execution(execution_id)
        
        if cancelled:
            # Update execution status
            execution.status = WorkflowStatus.CANCELLED
            execution.end_time = execution.end_time or execution.start_time
            await registry.store_workflow_execution(execution)
            
            return {"message": f"Execution {execution_id} cancelled successfully"}
        else:
            return {"message": f"Execution {execution_id} was not running"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to cancel execution {execution_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{execution_id}/status")
async def get_execution_status(
    execution_id: str,
    registry: WorkflowRegistry = Depends(get_registry)
):
    """Get execution status and progress."""
    try:
        execution = await registry.get_workflow_execution(execution_id)
        if not execution:
            raise HTTPException(status_code=404, detail="Execution not found")
        
        # Calculate progress
        total_steps = len(execution.step_executions)
        completed_steps = sum(
            1 for step in execution.step_executions 
            if step.status in ["completed", "skipped", "failed"]
        )
        
        progress_percentage = (completed_steps / total_steps * 100) if total_steps > 0 else 0
        
        return {
            "execution_id": execution_id,
            "status": execution.status,
            "progress_percentage": round(progress_percentage, 2),
            "completed_steps": completed_steps,
            "total_steps": total_steps,
            "start_time": execution.start_time,
            "end_time": execution.end_time,
            "current_step": next(
                (step.step_id for step in execution.step_executions if step.status == "running"),
                None
            )
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get execution status {execution_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{execution_id}/logs")
async def get_execution_logs(
    execution_id: str,
    registry: WorkflowRegistry = Depends(get_registry)
):
    """Get detailed execution logs for debugging."""
    try:
        execution = await registry.get_workflow_execution(execution_id)
        if not execution:
            raise HTTPException(status_code=404, detail="Execution not found")
        
        logs = []
        for step_exec in execution.step_executions:
            step_log = {
                "step_id": step_exec.step_id,
                "status": step_exec.status,
                "start_time": step_exec.start_time,
                "end_time": step_exec.end_time,
                "input_data": step_exec.input_data,
                "output_data": step_exec.output_data,
                "error_message": step_exec.error_message,
                "agent_id": step_exec.agent_id,
                "retry_attempt": step_exec.retry_attempt
            }
            logs.append(step_log)
        
        return {
            "execution_id": execution_id,
            "workflow_id": execution.workflow_id,
            "status": execution.status,
            "context": execution.context,
            "step_logs": logs
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get execution logs {execution_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))