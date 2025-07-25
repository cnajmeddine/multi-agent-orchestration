# main.py - FastAPI app entry point for the workflow_service
# This file initializes and runs the FastAPI application for workflow management.

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

from services.workflow_service.config import settings
from services.workflow_service.routes import workflows, executions
from services.workflow_service.workflow_registry import WorkflowRegistry
from services.workflow_service.workflow_engine import WorkflowEngine

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Global instances
workflow_engine = None
cleanup_task = None

async def periodic_cleanup():
    """Background task to cleanup completed executions."""
    global workflow_engine
    while True:
        try:
            await asyncio.sleep(60)  # Run every minute
            if workflow_engine:
                await workflow_engine.cleanup_completed_executions()
        except Exception as e:
            logger.error(f"Periodic cleanup failed: {str(e)}")

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handle startup and shutdown events."""
    global workflow_engine, cleanup_task
    
    # Startup
    logger.info(f"Starting {settings.service_name} on port {settings.service_port}")
    
    # Test Redis connection
    try:
        registry = WorkflowRegistry()
        registry.redis_client.ping()
        logger.info("Redis connection established")
    except Exception as e:
        logger.error(f"Failed to connect to Redis: {str(e)}")
        raise HTTPException(status_code=500, detail="Redis connection failed")
    
    # Test Agent Service connection
    try:
        # workflow_engine = WorkflowEngine()
        from .workflow_engine import EventIntegratedWorkflowEngine
        workflow_engine = EventIntegratedWorkflowEngine()

        response = await workflow_engine.agent_client.get("/health")
        if response.status_code == 200:
            logger.info("Agent service connection established")
        else:
            logger.warning(f"Agent service returned status {response.status_code}")
    except Exception as e:
        logger.warning(f"Failed to connect to agent service: {str(e)}")
        logger.info("Workflow service will start anyway, but agent calls may fail")
    
    # Start background cleanup task
    cleanup_task = asyncio.create_task(periodic_cleanup())
    logger.info("Started periodic cleanup task")
    
    yield
    
    # Shutdown
    logger.info("Shutting down workflow service...")
    if cleanup_task:
        cleanup_task.cancel()
        try:
            await cleanup_task
        except asyncio.CancelledError:
            pass
    
    if workflow_engine:
        await workflow_engine.agent_client.aclose()
    
    logger.info("Workflow service shutdown complete")

# Create FastAPI app
app = FastAPI(
    title="AI Workflow Service",
    description="Orchestrates AI agents into complex multi-step workflows",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure properly for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(workflows.router)
app.include_router(executions.router)

@app.get("/")
async def root():
    """Root endpoint with service info."""
    return {
        "service": settings.service_name,
        "version": "1.0.0",
        "status": "running",
        "docs": "/docs",
        "health": "/health"
    }

@app.get("/health")
async def health_check():
    """Basic health check endpoint."""
    try:
        # Test Redis
        registry = WorkflowRegistry()
        registry.redis_client.ping()
        redis_status = "healthy"
    except Exception:
        redis_status = "unhealthy"
    
    try:
        # Test Agent Service
        response = await workflow_engine.agent_client.get("/health")
        agent_service_status = "healthy" if response.status_code == 200 else "degraded"
    except Exception:
        agent_service_status = "unhealthy"
    
    overall_status = "healthy" if redis_status == "healthy" else "degraded"
    
    return {
        "status": overall_status,
        "service": settings.service_name,
        "components": {
            "redis": redis_status,
            "agent_service": agent_service_status
        },
        "running_executions": len(workflow_engine.get_running_executions()) if workflow_engine else 0
    }

@app.get("/debug/agent-connection")
async def debug_agent_connection():
    """Debug agent service connection."""
    try:
        response = await workflow_engine.agent_client.get("/")
        return {
            "agent_service_url": settings.agent_service_url,
            "response_status": response.status_code,
            "response_data": response.json()
        }
    except Exception as e:
        return {
            "agent_service_url": settings.agent_service_url,
            "error": str(e)
        }

if __name__ == "__main__":
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=settings.service_port,
        reload=False,
        log_level=settings.log_level.lower()
    )