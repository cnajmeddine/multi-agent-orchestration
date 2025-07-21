# config.py - Service configuration
# This file contains configuration settings for the agent_service.

from pydantic_settings import BaseSettings
from typing import Optional
import os

class Settings(BaseSettings):
    # Redis Configuration
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_db: int = 0
    redis_password: Optional[str] = None
    
    # Service Configuration
    service_name: str = "agent-service"
    service_port: int = 8001
    log_level: str = "INFO"
    
    # Agent Configuration
    max_agents_per_type: int = 10
    agent_heartbeat_interval: int = 30  # seconds
    agent_timeout: int = 300  # seconds
    
    class Config:
        env_prefix = "AGENT_SERVICE_"
        env_file = ".env"

settings = Settings()