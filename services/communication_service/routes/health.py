# Health check endpoint for the communication service. 
# services/communication_service/routes/health.py
"""Health check endpoints for the communication service."""

from fastapi import APIRouter, HTTPException, Depends, Request
from typing import Dict, Any
import redis
from datetime import datetime
import logging

from ..config import settings

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/health", tags=["health"])

@router.get("/")
async def health_check():
    """Basic health check endpoint."""
    return {
        "status": "healthy",
        "service": settings.service_name,
        "timestamp": datetime.utcnow().isoformat(),
        "version": "1.0.0"
    }

@router.get("/detailed")
async def detailed_health_check(request: Request):
    """Detailed health check including all components."""
    try:
        health_data = {
            "status": "healthy",
            "service": settings.service_name,
            "timestamp": datetime.utcnow().isoformat(),
            "version": "1.0.0",
            "components": {}
        }
        
        # Check Redis connection
        redis_healthy = False
        redis_error = None
        try:
            redis_client = redis.Redis(
                host=settings.redis_host,
                port=settings.redis_port,
                db=settings.redis_db,
                password=settings.redis_password,
                decode_responses=True
            )
            redis_client.ping()
            redis_healthy = True
            
            # Get Redis info
            redis_info = redis_client.info()
            health_data["components"]["redis"] = {
                "status": "healthy",
                "connected_clients": redis_info.get("connected_clients", 0),
                "used_memory_human": redis_info.get("used_memory_human", "unknown"),
                "uptime_in_days": redis_info.get("uptime_in_days", 0)
            }
            
        except Exception as e:
            redis_error = str(e)
            health_data["components"]["redis"] = {
                "status": "unhealthy",
                "error": redis_error
            }
        
        # Check Message Bus
        if hasattr(request.app.state, 'message_bus'):
            message_bus = request.app.state.message_bus
            health_data["components"]["message_bus"] = {
                "status": "healthy" if message_bus.running else "stopped",
                "active_consumers": len(message_bus.consumers),
                "consumer_ids": list(message_bus.consumers.keys())
            }
        else:
            health_data["components"]["message_bus"] = {
                "status": "not_initialized"
            }
        
        # Check Event Publisher
        if hasattr(request.app.state, 'event_publisher'):
            event_publisher = request.app.state.event_publisher
            try:
                event_stats = await event_publisher.get_event_stats()
                health_data["components"]["event_publisher"] = {
                    "status": "healthy" if event_publisher.running else "stopped",
                    "active_subscriptions": event_stats.get("active_subscriptions", 0),
                    "stream_count": len(event_stats.get("stream_info", {}))
                }
            except Exception as e:
                health_data["components"]["event_publisher"] = {
                    "status": "error",
                    "error": str(e)
                }
        else:
            health_data["components"]["event_publisher"] = {
                "status": "not_initialized"
            }
        
        # Check Webhook Manager
        if hasattr(request.app.state, 'webhook_manager'):
            webhook_manager = request.app.state.webhook_manager
            try:
                webhook_stats = await webhook_manager.get_webhook_stats()
                health_data["components"]["webhook_manager"] = {
                    "status": "healthy" if webhook_manager.running else "stopped",
                    "total_webhooks": webhook_stats.get("total_webhooks", 0),
                    "active_webhooks": webhook_stats.get("active_webhooks", 0),
                    "queue_size": webhook_stats.get("queue_size", 0),
                    "active_workers": webhook_stats.get("active_workers", 0)
                }
            except Exception as e:
                health_data["components"]["webhook_manager"] = {
                    "status": "error",
                    "error": str(e)
                }
        else:
            health_data["components"]["webhook_manager"] = {
                "status": "not_initialized"
            }
        
        # Check Queue Manager
        if hasattr(request.app.state, 'queue_manager'):
            queue_manager = request.app.state.queue_manager
            try:
                queue_stats = await queue_manager.get_all_queue_stats()
                total_pending = sum(qs.pending_messages for qs in queue_stats)
                total_processing = sum(qs.processing_messages for qs in queue_stats)
                
                health_data["components"]["queue_manager"] = {
                    "status": "healthy" if queue_manager.running else "stopped",
                    "total_queues": len(queue_stats),
                    "total_pending_messages": total_pending,
                    "total_processing_messages": total_processing,
                    "active_processors": len(queue_manager.processors)
                }
            except Exception as e:
                health_data["components"]["queue_manager"] = {
                    "status": "error",
                    "error": str(e)
                }
        else:
            health_data["components"]["queue_manager"] = {
                "status": "not_initialized"
            }
        
        # Overall status
        component_statuses = [
            comp.get("status", "unknown") 
            for comp in health_data["components"].values()
        ]
        
        if any(status == "unhealthy" for status in component_statuses):
            health_data["status"] = "unhealthy"
        elif any(status in ["error", "not_initialized"] for status in component_statuses):
            health_data["status"] = "degraded"
        
        # Configuration info
        health_data["config"] = {
            "redis_host": settings.redis_host,
            "redis_port": settings.redis_port,
            "redis_db": settings.redis_db,
            "service_port": settings.service_port,
            "max_concurrent_webhooks": settings.max_concurrent_webhooks,
            "max_concurrent_queue_processors": settings.max_concurrent_queue_processors,
            "message_retention_hours": settings.message_retention_hours
        }
        
        return health_data
        
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        return {
            "status": "error",
            "service": settings.service_name,
            "timestamp": datetime.utcnow().isoformat(),
            "error": str(e)
        }

@router.get("/readiness")
async def readiness_check(request: Request):
    """Readiness check for Kubernetes/container orchestration."""
    try:
        # Check if all required components are initialized and running
        required_components = [
            'message_bus', 'event_publisher', 'webhook_manager', 'queue_manager'
        ]
        
        for component in required_components:
            if not hasattr(request.app.state, component):
                raise HTTPException(
                    status_code=503, 
                    detail=f"Component {component} not initialized"
                )
            
            component_obj = getattr(request.app.state, component)
            if hasattr(component_obj, 'running') and not component_obj.running:
                raise HTTPException(
                    status_code=503, 
                    detail=f"Component {component} not running"
                )
        
        # Test Redis connection
        redis_client = redis.Redis(
            host=settings.redis_host,
            port=settings.redis_port,
            db=settings.redis_db,
            password=settings.redis_password,
            decode_responses=True
        )
        redis_client.ping()
        
        return {
            "status": "ready",
            "service": settings.service_name,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Readiness check failed: {str(e)}")
        raise HTTPException(status_code=503, detail=f"Service not ready: {str(e)}")

@router.get("/liveness")
async def liveness_check():
    """Liveness check for Kubernetes/container orchestration."""
    return {
        "status": "alive",
        "service": settings.service_name,
        "timestamp": datetime.utcnow().isoformat()
    }