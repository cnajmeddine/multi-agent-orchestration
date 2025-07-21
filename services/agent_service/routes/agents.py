# agents.py - Agent CRUD endpoints
# This file defines the API endpoints for managing agents.

from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from typing import List, Optional
import logging

from ..models import (
    AgentMetadata, AgentRegistrationRequest, AgentHealthCheck, 
    AgentRequest, AgentResponse, AgentStatus
)
from ..agent_registry import AgentRegistry
from ..agent_types.text_agent import TextProcessingAgent
from ..agent_types.analysis_agent import DataAnalysisAgent

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/agents", tags=["agents"])

# Dependency to get registry instance
def get_registry():
    return AgentRegistry()

# In-memory store for actual agent instances (PoC only)
_agent_instances = {}

@router.post("/register", response_model=AgentMetadata)
async def register_agent(
    request: AgentRegistrationRequest,
    registry: AgentRegistry = Depends(get_registry)
):
    """Register a new agent."""
    try:
        # Create agent metadata
        agent_metadata = AgentMetadata(
            name=request.name,
            agent_type=request.agent_type,
            capabilities=request.capabilities,
            config=request.config,
            max_concurrent_tasks=request.max_concurrent_tasks,
            status=AgentStatus.IDLE
        )
        
        # Register in Redis
        success = await registry.register_agent(agent_metadata)
        if not success:
            raise HTTPException(status_code=500, detail="Failed to register agent")
        
        # Create actual agent instance (PoC: store in memory)
        if request.agent_type == "text_processor":
            agent_instance = TextProcessingAgent(agent_metadata.agent_id, request.config)
        elif request.agent_type == "data_analyzer":
            agent_instance = DataAnalysisAgent(agent_metadata.agent_id, request.config)
        else:
            raise HTTPException(status_code=400, detail=f"Unknown agent type: {request.agent_type}")
        
        _agent_instances[agent_metadata.agent_id] = agent_instance
        
        logger.info(f"Successfully registered agent {agent_metadata.agent_id}")
        return agent_metadata
        
    except Exception as e:
        logger.error(f"Failed to register agent: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/unregister/{agent_id}")
async def unregister_agent(
    agent_id: str,
    registry: AgentRegistry = Depends(get_registry)
):
    """Unregister an agent."""
    try:
        success = await registry.unregister_agent(agent_id)
        if not success:
            raise HTTPException(status_code=404, detail="Agent not found")
        
        # Remove from memory
        _agent_instances.pop(agent_id, None)
        
        return {"message": f"Agent {agent_id} unregistered successfully"}
        
    except Exception as e:
        logger.error(f"Failed to unregister agent {agent_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/", response_model=List[AgentMetadata])
async def list_agents(
    agent_type: Optional[str] = None,
    registry: AgentRegistry = Depends(get_registry)
):
    """List all agents or agents of a specific type."""
    try:
        if agent_type:
            agents = await registry.get_agents_by_type(agent_type)
        else:
            # Get all active agents
            stats = await registry.get_registry_stats()
            all_agents = []
            for atype in stats.get("agents_by_type", {}):
                agents = await registry.get_agents_by_type(atype)
                all_agents.extend(agents)
            return all_agents
        
        return agents
        
    except Exception as e:
        logger.error(f"Failed to list agents: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{agent_id}", response_model=AgentMetadata)
async def get_agent(
    agent_id: str,
    registry: AgentRegistry = Depends(get_registry)
):
    """Get specific agent details."""
    try:
        agent = await registry.get_agent(agent_id)
        if not agent:
            raise HTTPException(status_code=404, detail="Agent not found")
        
        return agent
        
    except Exception as e:
        logger.error(f"Failed to get agent {agent_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/execute", response_model=AgentResponse)
async def execute_task(
    request: AgentRequest,
    registry: AgentRegistry = Depends(get_registry)
):
    """Execute a task on an available agent."""
    try:
        # Find available agent
        agent = await registry.find_available_agent(request.agent_type)
        if not agent:
            raise HTTPException(
                status_code=503, 
                detail=f"No available agents of type {request.agent_type}"
            )
        
        # Get agent instance
        agent_instance = _agent_instances.get(agent.agent_id)
        if not agent_instance:
            raise HTTPException(status_code=500, detail="Agent instance not found")
        
        # Update load before execution
        await registry.update_agent_load(agent.agent_id, agent.current_load + 1)
        
        try:
            # Execute task
            response = await agent_instance.execute_request(request)
            return response
        finally:
            # Update load after execution
            await registry.update_agent_load(agent.agent_id, agent.current_load)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to execute task: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/heartbeat/{agent_id}")
async def agent_heartbeat(
    agent_id: str,
    health_data: AgentHealthCheck,
    registry: AgentRegistry = Depends(get_registry)
):
    """Update agent heartbeat."""
    try:
        success = await registry.heartbeat(agent_id, health_data)
        if not success:
            raise HTTPException(status_code=404, detail="Agent not found")
        
        return {"message": "Heartbeat updated successfully"}
        
    except Exception as e:
        logger.error(f"Failed to update heartbeat for {agent_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
    
@router.get("/debug/{agent_id}")
async def debug_agent(
    agent_id: str,
    registry: AgentRegistry = Depends(get_registry)
):
    """Debug agent data in Redis."""
    try:
        # Get raw Redis data
        agent_key = f"agent:{agent_id}"
        raw_data = registry.redis_client.hgetall(agent_key)
        
        # Try to parse it
        agent = await registry.get_agent(agent_id)
        
        return {
            "agent_id": agent_id,
            "raw_redis_data": raw_data,
            "parsed_agent": agent.dict() if agent else None,
            "agent_available": agent.status in [AgentStatus.IDLE, AgentStatus.BUSY] if agent else False
        }
        
    except Exception as e:
        return {"error": str(e), "agent_id": agent_id}