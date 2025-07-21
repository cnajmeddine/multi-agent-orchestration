# models.py - Pydantic models for agents
# This file defines the data models used for agent representation and validation.

from pydantic import BaseModel, Field, field_validator
from typing import Dict, List, Optional, Any, Literal
from datetime import datetime
from enum import Enum
import uuid

class AgentStatus(str, Enum):
    INITIALIZING = "initializing"
    IDLE = "idle"
    BUSY = "busy"
    ERROR = "error"
    OFFLINE = "offline"

class AgentCapability(BaseModel):
    name: str
    description: str
    input_types: List[str]  # e.g., ["text", "json", "csv"]
    output_types: List[str]  # e.g., ["text", "json", "image"]
    max_concurrent_tasks: int = 1

class AgentMetadata(BaseModel):
    agent_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    agent_type: str  # e.g., "text_processor", "data_analyzer"
    capabilities: List[AgentCapability]
    status: AgentStatus = AgentStatus.INITIALIZING
    
    # Runtime info
    current_load: int = 0  # number of active tasks
    last_heartbeat: datetime = Field(default_factory=datetime.utcnow)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Configuration
    config: Dict[str, Any] = Field(default_factory=dict)
    max_concurrent_tasks: int = 1
    
    @field_validator('agent_id')
    @classmethod
    def validate_agent_id(cls, v):
        if not v:
            return str(uuid.uuid4())
        return v

class AgentRequest(BaseModel):
    task_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    agent_type: str
    input_data: Dict[str, Any]
    priority: int = Field(default=1, ge=1, le=10)
    timeout: int = Field(default=300, gt=0)  # seconds
    context: Optional[Dict[str, Any]] = None

class AgentResponse(BaseModel):
    task_id: str
    agent_id: str
    success: bool
    output_data: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    execution_time: float  # seconds
    timestamp: datetime = Field(default_factory=datetime.utcnow)

class AgentRegistrationRequest(BaseModel):
    name: str
    agent_type: str
    capabilities: List[AgentCapability]
    config: Dict[str, Any] = Field(default_factory=dict)
    max_concurrent_tasks: int = Field(default=1, gt=0)

class AgentHealthCheck(BaseModel):
    agent_id: str
    status: AgentStatus
    current_load: int
    memory_usage: Optional[float] = None  # percentage
    cpu_usage: Optional[float] = None     # percentage
    timestamp: datetime = Field(default_factory=datetime.utcnow)