# Configuration settings and environment variables for the communication service. 
# services/communication_service/config.py
"""Configuration settings for the communication service."""

from pydantic_settings import BaseSettings
from typing import Optional, List
import os

class Settings(BaseSettings):
    # Redis Configuration
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_db: int = 2  # Different DB from other services
    redis_password: Optional[str] = None
    
    # Service Configuration
    service_name: str = "communication-service"
    service_port: int = 8004
    log_level: str = "INFO"
    
    # Message Bus Configuration
    max_message_size: int = 1024 * 1024  # 1MB
    message_retention_hours: int = 24
    consumer_group_prefix: str = "comm_service"
    stream_prefix: str = "workflow_events"
    
    # Event Configuration
    event_batch_size: int = 100
    event_processing_interval: int = 1  # seconds
    max_event_retries: int = 3
    event_retry_delay: int = 5  # seconds
    
    # Webhook Configuration
    webhook_timeout: int = 30  # seconds
    webhook_retry_attempts: int = 3
    webhook_retry_backoff: float = 2.0  # exponential backoff multiplier
    max_webhook_payload_size: int = 10 * 1024 * 1024  # 10MB
    webhook_signature_header: str = "X-Webhook-Signature"
    
    # Queue Configuration
    dead_letter_queue_prefix: str = "dlq"
    queue_processing_batch_size: int = 50
    queue_visibility_timeout: int = 300  # seconds
    max_queue_retries: int = 5
    
    # External Service URLs
    agent_service_url: str = "http://localhost:8001"
    workflow_service_url: str = "http://localhost:8002"
    
    # Security
    webhook_secret_key: Optional[str] = None
    allowed_webhook_domains: List[str] = []  # Empty means all allowed
    
    # Performance
    max_concurrent_webhooks: int = 100
    max_concurrent_queue_processors: int = 20
    
    class Config:
        env_prefix = "COMM_SERVICE_"
        env_file = ".env"

settings = Settings()