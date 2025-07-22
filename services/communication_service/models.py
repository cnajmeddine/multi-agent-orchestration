# Data models and schemas for messages, events, and communication payloads. 
# services/communication_service/models.py
"""Data models for the communication service."""

from pydantic import BaseModel, Field, HttpUrl, field_validator
from typing import Dict, List, Optional, Any, Union, Literal
from datetime import datetime
from enum import Enum
import uuid

# Event Models
class EventType(str, Enum):
    WORKFLOW_STARTED = "workflow.started"
    WORKFLOW_COMPLETED = "workflow.completed"
    WORKFLOW_FAILED = "workflow.failed"
    WORKFLOW_CANCELLED = "workflow.cancelled"
    STEP_STARTED = "step.started"
    STEP_COMPLETED = "step.completed"
    STEP_FAILED = "step.failed"
    STEP_RETRYING = "step.retrying"
    AGENT_REGISTERED = "agent.registered"
    AGENT_UNREGISTERED = "agent.unregistered"
    AGENT_HEALTH_CHANGED = "agent.health_changed"
    SYSTEM_ALERT = "system.alert"

class EventPriority(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class Event(BaseModel):
    event_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    event_type: EventType
    source_service: str
    source_id: str  # workflow_id, agent_id, etc.
    priority: EventPriority = EventPriority.MEDIUM
    payload: Dict[str, Any] = Field(default_factory=dict)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    correlation_id: Optional[str] = None
    retry_count: int = 0
    
    @field_validator('payload')
    @classmethod
    def validate_payload_size(cls, v):
        # Basic size check (can be enhanced)
        import json
        if len(json.dumps(v)) > 1024 * 1024:  # 1MB
            raise ValueError("Event payload too large")
        return v

# Message Models
class MessageStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    DEAD_LETTER = "dead_letter"

class Message(BaseModel):
    message_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    queue_name: str
    payload: Dict[str, Any]
    priority: int = Field(default=1, ge=1, le=10)
    status: MessageStatus = MessageStatus.PENDING
    created_at: datetime = Field(default_factory=datetime.utcnow)
    scheduled_at: Optional[datetime] = None
    processed_at: Optional[datetime] = None
    retry_count: int = 0
    max_retries: int = 3
    error_message: Optional[str] = None
    processing_timeout: int = 300  # seconds

# Webhook Models
class WebhookStatus(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    FAILED = "failed"

class WebhookEventFilter(BaseModel):
    event_types: List[EventType] = Field(default_factory=list)
    source_services: List[str] = Field(default_factory=list)
    priority_levels: List[EventPriority] = Field(default_factory=list)

class Webhook(BaseModel):
    webhook_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    url: HttpUrl
    event_filter: WebhookEventFilter = Field(default_factory=WebhookEventFilter)
    secret_token: Optional[str] = None
    status: WebhookStatus = WebhookStatus.ACTIVE
    headers: Dict[str, str] = Field(default_factory=dict)
    timeout: int = Field(default=30, gt=0, le=300)
    retry_config: Dict[str, Any] = Field(default_factory=lambda: {
        "max_attempts": 3,
        "backoff_multiplier": 2.0,
        "initial_delay": 1
    })
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_triggered_at: Optional[datetime] = None
    success_count: int = 0
    failure_count: int = 0

class WebhookDelivery(BaseModel):
    delivery_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    webhook_id: str
    event_id: str
    attempt: int = 1
    status: Literal["pending", "success", "failed"] = "pending"
    response_status: Optional[int] = None
    response_body: Optional[str] = None
    error_message: Optional[str] = None
    delivered_at: Optional[datetime] = None
    duration_ms: Optional[int] = None

# Request/Response Models
class EventPublishRequest(BaseModel):
    event_type: EventType
    source_service: str
    source_id: str
    priority: EventPriority = EventPriority.MEDIUM
    payload: Dict[str, Any] = Field(default_factory=dict)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    correlation_id: Optional[str] = None

class MessageEnqueueRequest(BaseModel):
    queue_name: str
    payload: Dict[str, Any]
    priority: int = Field(default=1, ge=1, le=10)
    delay_seconds: int = Field(default=0, ge=0)
    max_retries: int = Field(default=3, ge=0, le=10)

class WebhookCreateRequest(BaseModel):
    name: str
    url: HttpUrl
    event_filter: WebhookEventFilter = Field(default_factory=WebhookEventFilter)
    secret_token: Optional[str] = None
    headers: Dict[str, str] = Field(default_factory=dict)
    timeout: int = Field(default=30, gt=0, le=300)

class WebhookUpdateRequest(BaseModel):
    name: Optional[str] = None
    url: Optional[HttpUrl] = None
    event_filter: Optional[WebhookEventFilter] = None
    secret_token: Optional[str] = None
    headers: Optional[Dict[str, str]] = None
    timeout: Optional[int] = Field(default=None, gt=0, le=300)
    status: Optional[WebhookStatus] = None

# Stats and Monitoring Models
class ServiceStats(BaseModel):
    events_published: int = 0
    events_processed: int = 0
    messages_queued: int = 0
    messages_processed: int = 0
    webhooks_delivered: int = 0
    webhooks_failed: int = 0
    active_streams: int = 0
    active_queues: int = 0
    active_webhooks: int = 0

class QueueStats(BaseModel):
    queue_name: str
    pending_messages: int = 0
    processing_messages: int = 0
    completed_messages: int = 0
    failed_messages: int = 0
    dead_letter_messages: int = 0
    average_processing_time: float = 0.0

class StreamInfo(BaseModel):
    stream_name: str
    length: int = 0
    consumer_groups: List[str] = Field(default_factory=list)
    last_event_id: Optional[str] = None
    first_event_id: Optional[str] = None