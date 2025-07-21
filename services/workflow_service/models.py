# models.py - Workflow definitions and execution state
# This file defines the data models for workflows and their execution state.

from pydantic import BaseModel, Field, validator
from typing import Dict, List, Optional, Any, Union, Literal
from datetime import datetime
from enum import Enum
import uuid

class WorkflowStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class StepStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"

class WorkflowStep(BaseModel):
    step_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    agent_type: str
    input_mapping: Dict[str, str]  # Maps step inputs to workflow context
    output_mapping: Dict[str, str]  # Maps step outputs to workflow context
    depends_on: List[str] = Field(default_factory=list)  # Step IDs this depends on
    condition: Optional[str] = None  # Simple condition for conditional execution
    timeout: int = Field(default=300, gt=0)
    retry_count: int = Field(default=0, ge=0)

class WorkflowDefinition(BaseModel):
    workflow_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    description: Optional[str] = None
    version: str = "1.0"
    steps: List[WorkflowStep]
    global_timeout: int = Field(default=3600, gt=0)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    created_by: str = "system"

class StepExecution(BaseModel):
    step_id: str
    execution_id: str
    status: StepStatus = StepStatus.PENDING
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    input_data: Optional[Dict[str, Any]] = None
    output_data: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    agent_id: Optional[str] = None
    retry_attempt: int = 0

class WorkflowExecution(BaseModel):
    execution_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    workflow_id: str
    status: WorkflowStatus = WorkflowStatus.PENDING
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    input_data: Dict[str, Any] = Field(default_factory=dict)
    context: Dict[str, Any] = Field(default_factory=dict)  # Shared data between steps
    step_executions: List[StepExecution] = Field(default_factory=list)
    error_message: Optional[str] = None
    created_by: str = "system"

class WorkflowExecutionRequest(BaseModel):
    input_data: Dict[str, Any] = Field(default_factory=dict)
    priority: int = Field(default=1, ge=1, le=10)
    tags: List[str] = Field(default_factory=list)

class WorkflowCreateRequest(BaseModel):
    name: str
    description: Optional[str] = None
    steps: List[WorkflowStep]
    global_timeout: int = Field(default=3600, gt=0)