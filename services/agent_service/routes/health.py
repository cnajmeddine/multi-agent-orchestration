# health.py - Health check endpoints
# This file defines endpoints for checking the health of the agent_service.

from fastapi import APIRouter, Depends
from typing import Dict, Any
import redis
from datetime import datetime

from ..agent_registry import AgentRegistry
from ..config import settings

router = APIRouter(prefix="/health", tags=["health"])

def get_registry():
    return AgentRegistry()

@router.get("/")
async def health_check():
    """Basic health check endpoint."""
    return {
        "status": "healthy",
        "service": "agent-service",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "1.0.0"
    }

@router.get("/detailed")
async def detailed_health_check(registry: AgentRegistry = Depends(get_registry)):
    """Detailed health check including Redis and agent status."""
    try:
        # Test Redis connection
        redis_healthy = False
        try:
            registry.redis_client.ping()
            redis_healthy = True
        except Exception as e:
            redis_error = str(e)
        
        # Get registry stats
        stats = await registry.get_registry_stats()
        
        # Cleanup dead agents
        cleaned_agents = await registry.cleanup_dead_agents()
        
        health_data = {
            "status": "healthy" if redis_healthy else "degraded",
            "service": "agent-service",
            "timestamp": datetime.utcnow().isoformat(),
            "components": {
                "redis": {
                    "status": "healthy" if redis_healthy else "unhealthy",
                    "error": None if redis_healthy else redis_error
                },
                "agent_registry": {
                    "status": "healthy",
                    "total_agents": stats.get("total_active_agents", 0),
                    "agents_by_type": stats.get("agents_by_type", {}),
                    "cleaned_dead_agents": cleaned_agents
                }
            },
            "config": {
                "redis_host": settings.redis_host,
                "redis_port": settings.redis_port,
                "max_agents_per_type": settings.max_agents_per_type,
                "agent_timeout": settings.agent_timeout
            }
        }
        
        return health_data
        
    except Exception as e:
        return {
            "status": "unhealthy",
            "service": "agent-service", 
            "timestamp": datetime.utcnow().isoformat(),
            "error": str(e)
        }