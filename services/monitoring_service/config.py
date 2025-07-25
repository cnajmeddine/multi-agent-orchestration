# services/monitoring_service/config.py
# Configuration settings for the monitoring service

from pydantic_settings import BaseSettings
from typing import Optional, List, Dict
import os

class Settings(BaseSettings):
    # Service Configuration
    service_name: str = "monitoring-service"
    service_port: int = 8003
    log_level: str = "INFO"
    
    # Redis Configuration (for persistent storage if needed)
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_db: int = 3  # Different DB from other services
    redis_password: Optional[str] = None
    
    # Monitoring Configuration
    metrics_retention_hours: int = 24  # How long to keep metrics in memory
    max_metrics_per_type: int = 1000   # Max data points per metric type
    health_check_interval: int = 30    # Seconds between health checks
    health_check_timeout: int = 10     # Timeout for health check requests
    
    # Alert Configuration  
    max_alerts: int = 1000             # Maximum alerts to keep
    alert_cleanup_hours: int = 168     # Clean up resolved alerts after 7 days
    critical_alert_retention_hours: int = 720  # Keep critical alerts for 30 days
    
    # Performance Counter Configuration
    counter_reset_interval: int = 86400  # Reset counters daily (seconds)
    
    # Dashboard Configuration
    dashboard_refresh_interval: int = 5   # Seconds between dashboard updates
    recent_events_limit: int = 100        # Number of recent events to keep
    
    # Service URLs for health checks
    agent_service_url: str = "http://localhost:8001"
    workflow_service_url: str = "http://localhost:8002" 
    communication_service_url: str = "http://localhost:8004"
    
    # Services to monitor
    monitored_services: Dict[str, str] = {
        "agent-service": "http://localhost:8001",
        "workflow-service": "http://localhost:8002",
        "communication-service": "http://localhost:8004"
    }
    
    # Default Alert Conditions
    default_alert_conditions: List[Dict[str, any]] = [
        {
            "metric_name": "workflow_execution_time",
            "operator": "gt",
            "threshold": 300.0,  # 5 minutes
            "severity": "warning",
            "description": "Workflow execution taking longer than 5 minutes"
        },
        {
            "metric_name": "agent_response_time", 
            "operator": "gt",
            "threshold": 30.0,   # 30 seconds
            "severity": "warning",
            "description": "Agent response time exceeding 30 seconds"
        },
        {
            "metric_name": "service_health",
            "operator": "eq", 
            "threshold": 0.0,    # 0 = unhealthy
            "severity": "critical",
            "description": "Service health check failed"
        },
        {
            "metric_name": "error_rate",
            "operator": "gt",
            "threshold": 0.1,    # 10% error rate
            "severity": "critical", 
            "description": "Error rate exceeding 10%"
        },
        {
            "metric_name": "memory_usage",
            "operator": "gt",
            "threshold": 90.0,   # 90% memory usage
            "severity": "warning",
            "description": "Memory usage exceeding 90%"
        }
    ]
    
    # Notification Configuration (for future webhook/email alerts)
    enable_notifications: bool = False
    notification_webhook_url: Optional[str] = None
    notification_email: Optional[str] = None
    
    # Data Storage Configuration
    use_persistent_storage: bool = False  # Set to True to use Redis for persistence
    metrics_backup_interval: int = 3600   # Backup metrics every hour (if persistent)
    
    # Security Configuration
    enable_auth: bool = False
    api_key: Optional[str] = None
    allowed_origins: List[str] = ["*"]  # CORS origins
    
    # Performance Configuration
    max_concurrent_health_checks: int = 10
    batch_size_metrics: int = 100
    cleanup_task_interval: int = 300  # Run cleanup every 5 minutes
    
    class Config:
        env_prefix = "MONITORING_SERVICE_"
        env_file = ".env"

settings = Settings()