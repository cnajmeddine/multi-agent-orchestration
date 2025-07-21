# config.py - Service configuration for workflow_service
# This file contains configuration settings for the workflow_service.

from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    # Redis Configuration
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_db: int = 1  # Different DB from agent service
    redis_password: Optional[str] = None
    
    # Service Configuration
    service_name: str = "workflow-service"
    service_port: int = 8002
    log_level: str = "INFO"
    
    # Agent Service Integration
    agent_service_url: str = "http://localhost:8001"
    
    # Workflow Configuration
    max_concurrent_workflows: int = 50
    workflow_cleanup_interval: int = 3600  # seconds
    default_step_timeout: int = 300  # seconds
    
    class Config:
        env_prefix = "WORKFLOW_SERVICE_"
        env_file = ".env"

settings = Settings()