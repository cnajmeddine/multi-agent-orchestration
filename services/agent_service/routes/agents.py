# agents.py - Agent CRUD endpoints
# This file defines the API endpoints for managing agents.

from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks, Request
from typing import List, Optional
import logging

from ..models import (
    AgentMetadata, AgentRegistrationRequest, AgentHealthCheck, 
    AgentRequest, AgentResponse, AgentStatus
)
from ..agent_registry import AgentRegistry
from ..agent_types.text_agent import TextProcessingAgent
from ..agent_types.analysis_agent import DataAnalysisAgent
from ..event_publisher import event_publisher

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/agents", tags=["agents"])

# Dependency to get registry instance
def get_registry():
    return AgentRegistry()

def get_bootstrap(request: Request):
    """Get bootstrap instance from app state."""
    if not hasattr(request.app.state, 'bootstrap'):
        raise HTTPException(status_code=500, detail="Bootstrap not initialized")
    return request.app.state.bootstrap

@router.post("/register", response_model=AgentMetadata)
async def register_agent(
    request_data: AgentRegistrationRequest,
    request: Request,
    registry: AgentRegistry = Depends(get_registry)
):
    """Register a new agent."""
    try:
        bootstrap = get_bootstrap(request)
        
        # Create agent metadata
        agent_metadata = AgentMetadata(
            name=request_data.name,
            agent_type=request_data.agent_type,
            capabilities=request_data.capabilities,
            config=request_data.config,
            max_concurrent_tasks=request_data.max_concurrent_tasks,
            status=AgentStatus.IDLE
        )
        
        # Register in Redis
        success = await registry.register_agent(agent_metadata)
        if not success:
            raise HTTPException(status_code=500, detail="Failed to register agent")
        
        # Create actual agent instance
        if request_data.agent_type == "text_processor":
            agent_instance = TextProcessingAgent(agent_metadata.agent_id, request_data.config)
        elif request_data.agent_type == "data_analyzer":
            agent_instance = DataAnalysisAgent(agent_metadata.agent_id, request_data.config)
        else:
            raise HTTPException(status_code=400, detail=f"Unknown agent type: {request_data.agent_type}")
        
        # Store in bootstrap
        bootstrap.add_agent_instance(agent_metadata.agent_id, agent_instance)
        
        logger.info(f"Successfully registered agent {agent_metadata.agent_id}")
        await event_publisher.publish_agent_registered(agent_metadata)
        return agent_metadata
        
    except Exception as e:
        logger.error(f"Failed to register agent: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/unregister/{agent_id}")
async def unregister_agent(
    agent_id: str,
    request: Request,
    registry: AgentRegistry = Depends(get_registry)
):
    """Unregister an agent."""
    try:
        bootstrap = get_bootstrap(request)
        
        success = await registry.unregister_agent(agent_id)
        if not success:
            raise HTTPException(status_code=404, detail="Agent not found")
        
        # Remove from bootstrap
        bootstrap.remove_agent_instance(agent_id)

        await event_publisher.publish_agent_unregistered(agent_id)
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
    agent_request: AgentRequest,
    request: Request,
    registry: AgentRegistry = Depends(get_registry)
):
    """Execute a task on an available agent."""
    try:
        bootstrap = get_bootstrap(request)
        
        # Find available agent
        agent = await registry.find_available_agent(agent_request.agent_type)
        if not agent:
            raise HTTPException(
                status_code=503, 
                detail=f"No available agents of type {agent_request.agent_type}"
            )
        
        # Get agent instance from bootstrap
        agent_instance = bootstrap.get_agent_instance(agent.agent_id)
        if not agent_instance:
            logger.warning(f"Agent instance {agent.agent_id} not found in bootstrap, attempting recovery...")
            
            # Try to recover the agent instance
            await bootstrap.recover_agent_instances()
            agent_instance = bootstrap.get_agent_instance(agent.agent_id)
            
            if not agent_instance:
                raise HTTPException(status_code=500, detail="Agent instance not found and could not be recovered")
        
        # Update load before execution
        await registry.update_agent_load(agent.agent_id, agent.current_load + 1)
        
        try:
            # Execute task
            response = await agent_instance.execute_request(agent_request)

            # Publish task execution event
            await event_publisher.publish_task_executed(
                agent.agent_id,
                agent_request.task_id,
                response.execution_time,
                response.success,
                response.error_message
            )

            return response
        finally:
            # Update load after execution
            await registry.update_agent_load(agent.agent_id, max(0, agent.current_load - 1))
        
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

        agent = await registry.get_agent(agent_id)  # Get agent for max_tasks
        await event_publisher.publish_health_status(
            agent_id,
            health_data.status.value,
            health_data.current_load,
            agent.max_concurrent_tasks if agent else 1
        )
        
        return {"message": "Heartbeat updated successfully"}
        
    except Exception as e:
        logger.error(f"Failed to update heartbeat for {agent_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/debug/instances")
async def debug_agent_instances(request: Request):
    """Debug agent instances in bootstrap."""
    try:
        bootstrap = get_bootstrap(request)
        instances = bootstrap.agent_instances
        
        return {
            "total_instances": len(instances),
            "instance_ids": list(instances.keys()),
            "instance_types": {
                agent_id: type(instance).__name__ 
                for agent_id, instance in instances.items()
            }
        }
        
    except Exception as e:
        return {"error": str(e)}

@router.post("/bootstrap/recover")
async def recover_agents(request: Request):
    """Manually trigger agent recovery."""
    try:
        bootstrap = get_bootstrap(request)
        recovered = await bootstrap.recover_agent_instances()
        
        return {
            "message": f"Recovered {len(recovered)} agent instances",
            "recovered_agents": list(recovered.keys())
        }
        
    except Exception as e:
        logger.error(f"Manual agent recovery failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
    
@router.get("/debug/{agent_id}")
async def debug_agent(
    agent_id: str,
    request: Request,
    registry: AgentRegistry = Depends(get_registry)
):
    """Debug agent data in Redis and bootstrap."""
    try:
        bootstrap = get_bootstrap(request)
        
        # Get raw Redis data
        agent_key = f"agent:{agent_id}"
        raw_data = registry.redis_client.hgetall(agent_key)
        
        # Try to parse it
        agent = await registry.get_agent(agent_id)
        
        # Check if instance exists
        instance_exists = bootstrap.get_agent_instance(agent_id) is not None
        
        return {
            "agent_id": agent_id,
            "raw_redis_data": raw_data,
            "parsed_agent": agent.dict() if agent else None,
            "agent_available": agent.status in [AgentStatus.IDLE, AgentStatus.BUSY] if agent else False,
            "instance_exists": instance_exists,
            "total_instances": len(bootstrap.agent_instances)
        }
        
    except Exception as e:
        return {"error": str(e), "agent_id": agent_id}