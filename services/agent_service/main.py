# main.py - FastAPI app entry point for the agent_service
# This file initializes and runs the FastAPI application for agent management.

import asyncio
import logging
import sys
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

from services.agent_service.config import settings
from services.agent_service.routes import agents, health
from services.agent_service.agent_registry import AgentRegistry
from services.agent_service.agent_bootstrap import AgentBootstrap

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Global instances
cleanup_task = None
bootstrap = None

async def periodic_cleanup():
    """Background task to cleanup dead agents."""
    registry = AgentRegistry()
    while True:
        try:
            await asyncio.sleep(60)  # Run every minute
            cleaned = await registry.cleanup_dead_agents()
            if cleaned > 0:
                logger.info(f"Periodic cleanup removed {cleaned} dead agents")
        except Exception as e:
            logger.error(f"Periodic cleanup failed: {str(e)}")

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handle startup and shutdown events."""
    global cleanup_task, bootstrap
    
    # Startup
    logger.info(f"Starting {settings.service_name} on port {settings.service_port}")
    
    # Test Redis connection
    try:
        registry = AgentRegistry()
        registry.redis_client.ping()
        logger.info("Redis connection established")
    except Exception as e:
        logger.error(f"Failed to connect to Redis: {str(e)}")
        raise HTTPException(status_code=500, detail="Redis connection failed")
    
    # Initialize bootstrap
    bootstrap = AgentBootstrap(registry)
    
    # Try to recover existing agents first
    recovered_instances = await bootstrap.recover_agent_instances()
    
    # Bootstrap default agents if none exist
    if not recovered_instances:
        logger.info("No existing agents found, bootstrapping defaults...")
        await bootstrap.bootstrap_default_agents()
    else:
        logger.info(f"Recovered {len(recovered_instances)} existing agents")
    
    # Store bootstrap in app state for routes to access
    app.state.bootstrap = bootstrap
    
    # Start background cleanup task
    cleanup_task = asyncio.create_task(periodic_cleanup())
    logger.info("Started periodic cleanup task")
    
    yield
    
    # Shutdown
    logger.info("Shutting down agent service...")
    if cleanup_task:
        cleanup_task.cancel()
        try:
            await cleanup_task
        except asyncio.CancelledError:
            pass
    logger.info("Agent service shutdown complete")

# Create FastAPI app
app = FastAPI(
    title="AI Agent Service",
    description="Core agent management and execution service for AI Agent Orchestration Platform",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware for frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure properly for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(agents.router)
app.include_router(health.router)

@app.get("/")
async def root():
    """Root endpoint with service info."""
    agent_count = len(app.state.bootstrap.agent_instances) if hasattr(app.state, 'bootstrap') else 0
    return {
        "service": settings.service_name,
        "version": "1.0.0",
        "status": "running",
        "active_agents": agent_count,
        "docs": "/docs",
        "health": "/health"
    }

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=settings.service_port,
        reload=True,
        log_level=settings.log_level.lower()
    )