# services/communication_service/main.py - WORKING VERSION
"""Working main FastAPI application based on the no-lifespan approach."""

import asyncio
import logging
import sys
import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

from services.communication_service.config import settings
from services.communication_service.routes import events, webhooks, queues, health

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Create FastAPI app WITHOUT any lifespan or startup events
app = FastAPI(
    title="AI Communication Service",
    description="Reliable messaging, events, and webhook service for AI Agent Orchestration Platform",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure properly for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global state for components (initialized lazily like in no-lifespan version)
_components = {
    "message_bus": None,
    "event_publisher": None,
    "webhook_manager": None,
    "queue_manager": None
}

def get_or_create_component(component_name: str):
    """Lazy initialization of components (copied from working no-lifespan version)."""
    if _components[component_name] is None:
        try:
            if component_name == "message_bus":
                from services.communication_service.message_bus import MessageBus
                comp = MessageBus()
                # Start it immediately
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    # Create a task to start it
                    asyncio.create_task(comp.start())
                else:
                    loop.run_until_complete(comp.start())
                _components[component_name] = comp
                logger.info(f"Initialized and started {component_name}")
                
            elif component_name == "event_publisher":
                from services.communication_service.event_publisher import EventPublisher
                message_bus = get_or_create_component("message_bus")
                comp = EventPublisher(message_bus)
                # Start it immediately
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    asyncio.create_task(comp.start())
                else:
                    loop.run_until_complete(comp.start())
                _components[component_name] = comp
                logger.info(f"Initialized and started {component_name}")
                
            elif component_name == "webhook_manager":
                from services.communication_service.webhook_manager import WebhookManager
                comp = WebhookManager()
                # Start it immediately
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    asyncio.create_task(comp.start())
                else:
                    loop.run_until_complete(comp.start())
                _components[component_name] = comp
                logger.info(f"Initialized and started {component_name}")
                
            elif component_name == "queue_manager":
                from services.communication_service.queue_manager import QueueManager
                comp = QueueManager()
                # Start it immediately
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    asyncio.create_task(comp.start())
                else:
                    loop.run_until_complete(comp.start())
                _components[component_name] = comp
                logger.info(f"Initialized and started {component_name}")
                
        except Exception as e:
            logger.error(f"Failed to initialize {component_name}: {str(e)}")
            # Return a mock object instead of None (same as no-lifespan version)
            _components[component_name] = type('MockComponent', (), {
                'error': str(e),
                'get_webhook_stats': lambda: {"error": str(e)},
                'get_event_stats': lambda: {"error": str(e)},
                'get_all_queue_stats': lambda: [],
                'running': False
            })()
    
    return _components[component_name]

# Store components in app state for routes (this is what routes expect)
def ensure_app_state():
    """Ensure app.state has the components that routes expect."""
    if not hasattr(app.state, 'message_bus'):
        app.state.message_bus = get_or_create_component("message_bus")
    if not hasattr(app.state, 'event_publisher'):
        app.state.event_publisher = get_or_create_component("event_publisher")
    if not hasattr(app.state, 'webhook_manager'):
        app.state.webhook_manager = get_or_create_component("webhook_manager")
    if not hasattr(app.state, 'queue_manager'):
        app.state.queue_manager = get_or_create_component("queue_manager")

# Include routers
app.include_router(events.router)
app.include_router(webhooks.router)
app.include_router(queues.router)
app.include_router(health.router)

@app.get("/")
async def root():
    """Root endpoint with service info."""
    # Ensure components are available for any route that might need them
    ensure_app_state()
    
    return {
        "service": settings.service_name,
        "version": "1.0.0",
        "status": "running",
        "docs": "/docs",
        "health": "/health",
        "message": "Communication service with lazy initialization",
        "features": [
            "Redis Streams messaging",
            "Event publishing/subscription", 
            "Webhook delivery",
            "Message queues with DLQ",
            "Async processing"
        ]
    }

@app.get("/stats")
async def get_service_stats():
    """Get overall service statistics."""
    try:
        # Ensure components are initialized
        ensure_app_state()
        
        stats = {
            "service": settings.service_name,
            "timestamp": asyncio.get_event_loop().time(),
            "components": {}
        }
        
        # Event publisher stats
        event_publisher = _components.get("event_publisher")
        if event_publisher and not hasattr(event_publisher, 'error'):
            try:
                stats["components"]["events"] = await event_publisher.get_event_stats()
            except Exception as e:
                stats["components"]["events"] = {"error": str(e)}
        elif event_publisher:
            stats["components"]["events"] = {"error": getattr(event_publisher, 'error', 'Unknown error')}
        
        # Webhook manager stats
        webhook_manager = _components.get("webhook_manager")
        if webhook_manager and not hasattr(webhook_manager, 'error'):
            try:
                stats["components"]["webhooks"] = await webhook_manager.get_webhook_stats()
            except Exception as e:
                stats["components"]["webhooks"] = {"error": str(e)}
        elif webhook_manager:
            stats["components"]["webhooks"] = {"error": getattr(webhook_manager, 'error', 'Unknown error')}
        
        # Queue manager stats
        queue_manager = _components.get("queue_manager")
        if queue_manager and not hasattr(queue_manager, 'error'):
            try:
                queue_stats = await queue_manager.get_all_queue_stats()
                stats["components"]["queues"] = {
                    "total_queues": len(queue_stats),
                    "queue_details": [qs.dict() for qs in queue_stats]
                }
            except Exception as e:
                stats["components"]["queues"] = {"error": str(e)}
        elif queue_manager:
            stats["components"]["queues"] = {"error": getattr(queue_manager, 'error', 'Unknown error')}
        
        # Component status summary
        stats["component_status"] = {
            "initialized": [name for name, comp in _components.items() if comp is not None and not hasattr(comp, 'error')],
            "errors": [name for name, comp in _components.items() if comp is not None and hasattr(comp, 'error')],
            "not_initialized": [name for name, comp in _components.items() if comp is None]
        }
        
        return stats
        
    except Exception as e:
        logger.error(f"Failed to get service stats: {str(e)}")
        return {
            "service": settings.service_name,
            "error": str(e),
            "components": {}
        }

@app.get("/init")
async def initialize_all_components():
    """Manually initialize all components (useful for debugging)."""
    try:
        ensure_app_state()
        
        results = {}
        for comp_name in _components:
            comp = _components[comp_name]
            if comp is None:
                results[comp_name] = "not_initialized"
            elif hasattr(comp, 'error'):
                results[comp_name] = f"error: {comp.error}"
            else:
                results[comp_name] = "initialized_and_started"
        
        return {
            "message": "Component initialization attempted",
            "results": results,
            "app_state_updated": True
        }
        
    except Exception as e:
        logger.error(f"Failed to initialize components: {str(e)}")
        return {"error": str(e)}

if __name__ == "__main__":
    uvicorn.run(
        app,
        host="127.0.0.1",
        port=settings.service_port,
        reload=False,
        log_level=settings.log_level.lower()
    )