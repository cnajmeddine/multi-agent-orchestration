# services/monitoring_service/models.py
# Data models for the monitoring service

from pydantic import BaseModel, Field
from typing import Dict, List, Optional, Any, Literal
from datetime import datetime
from enum import Enum
import uuid

class AlertSeverity(str, Enum):
    CRITICAL = "critical"
    WARNING = "warning"
    INFO = "info"
    LOW = "low"

class ServiceStatus(str, Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"

class MetricPoint(BaseModel):
    timestamp: datetime
    value: float
    labels: Dict[str, str] = Field(default_factory=dict)

class Alert(BaseModel):
    alert_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    severity: AlertSeverity
    title: str
    description: str
    service: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    resolved_at: Optional[datetime] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    @property
    def is_active(self) -> bool:
        return self.resolved_at is None

class ServiceHealth(BaseModel):
    service_name: str
    status: ServiceStatus
    last_check: datetime
    response_time: float  # in seconds
    error_count: int
    uptime_percentage: float
    endpoint_url: Optional[str] = None
    version: Optional[str] = None
    
class MetricSummary(BaseModel):
    metric_name: str
    count: int
    latest_value: Optional[float] = None
    average: float = 0.0
    minimum: Optional[float] = None
    maximum: Optional[float] = None
    last_updated: Optional[datetime] = None

class PerformanceCounter(BaseModel):
    counter_name: str
    value: int
    last_increment: datetime = Field(default_factory=datetime.utcnow)
    
class EventRecord(BaseModel):
    event_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    event_type: str
    source_service: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    data: Dict[str, Any] = Field(default_factory=dict)

class AlertCondition(BaseModel):
    metric_name: str
    operator: Literal["gt", "lt", "eq", "gte", "lte"]  # greater than, less than, etc.
    threshold: float
    severity: AlertSeverity
    description: str = ""
    enabled: bool = True

class DashboardOverview(BaseModel):
    active_alerts: int
    critical_alerts: int
    healthy_services: int
    total_services: int
    workflow_success_rate: float
    total_workflows: int
    timestamp: datetime = Field(default_factory=datetime.utcnow)

class WorkflowMetrics(BaseModel):
    total_started: int = 0
    total_completed: int = 0
    total_failed: int = 0
    total_cancelled: int = 0
    average_execution_time: float = 0.0
    success_rate: float = 0.0
    
class AgentMetrics(BaseModel):
    total_calls: int = 0
    successful_calls: int = 0
    failed_calls: int = 0
    average_response_time: float = 0.0
    success_rate: float = 0.0

class SystemMetrics(BaseModel):
    cpu_usage: Optional[float] = None
    memory_usage: Optional[float] = None
    disk_usage: Optional[float] = None
    network_io: Optional[Dict[str, float]] = None
    
class MonitoringStats(BaseModel):
    workflow_metrics: WorkflowMetrics
    agent_metrics: AgentMetrics
    system_metrics: SystemMetrics
    service_health: List[ServiceHealth]
    active_alerts: List[Alert]
    recent_events: List[EventRecord]

# Request/Response Models
class MetricRecordRequest(BaseModel):
    metric_name: str
    value: float
    labels: Dict[str, str] = Field(default_factory=dict)

class CounterIncrementRequest(BaseModel):
    counter_name: str
    increment: int = 1

class AlertCreateRequest(BaseModel):
    severity: AlertSeverity
    title: str
    description: str
    service: str
    metadata: Dict[str, Any] = Field(default_factory=dict)

class HealthCheckRequest(BaseModel):
    service_name: str
    url: str
    timeout: int = 10

class AlertConditionRequest(BaseModel):
    metric_name: str
    operator: Literal["gt", "lt", "eq", "gte", "lte"]
    threshold: float
    severity: AlertSeverity
    description: str = ""