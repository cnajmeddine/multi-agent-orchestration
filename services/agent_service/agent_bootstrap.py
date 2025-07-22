# services/agent_service/agent_bootstrap.py
# Bootstrap default agents on service startup

import asyncio
import logging
from typing import Dict, List
from .models import AgentRegistrationRequest, AgentCapability
from .agent_registry import AgentRegistry
from .agent_types.text_agent import TextProcessingAgent
from .agent_types.analysis_agent import DataAnalysisAgent

logger = logging.getLogger(__name__)

class AgentBootstrap:
    """Bootstrap and manage default agents."""
    
    DEFAULT_AGENTS = [
        {
            "name": "default-text-processor-1",
            "agent_type": "text_processor", 
            "capabilities": [
                AgentCapability(
                    name="sentiment_analysis",
                    description="Analyze sentiment of text",
                    input_types=["text"],
                    output_types=["json"],
                    max_concurrent_tasks=5
                ),
                AgentCapability(
                    name="text_summarization",
                    description="Summarize text content",
                    input_types=["text"],
                    output_types=["text"],
                    max_concurrent_tasks=3
                )
            ],
            "max_concurrent_tasks": 5
        },
        {
            "name": "default-text-processor-2",
            "agent_type": "text_processor",
            "capabilities": [
                AgentCapability(
                    name="sentiment_analysis",
                    description="Analyze sentiment of text",
                    input_types=["text"],
                    output_types=["json"],
                    max_concurrent_tasks=5
                )
            ],
            "max_concurrent_tasks": 3
        },
        {
            "name": "default-data-analyzer-1",
            "agent_type": "data_analyzer",
            "capabilities": [
                AgentCapability(
                    name="statistical_analysis",
                    description="Perform statistical analysis on datasets",
                    input_types=["json", "csv"],
                    output_types=["json"],
                    max_concurrent_tasks=2
                ),
                AgentCapability(
                    name="data_summary",
                    description="Generate summary statistics for datasets",
                    input_types=["json", "csv"],
                    output_types=["json"],
                    max_concurrent_tasks=3
                )
            ],
            "max_concurrent_tasks": 2
        }
    ]
    
    def __init__(self, registry: AgentRegistry):
        self.registry = registry
        self.agent_instances: Dict[str, object] = {}
    
    async def bootstrap_default_agents(self) -> Dict[str, object]:
        """Create and register default agents."""
        logger.info("Bootstrapping default agents...")
        
        for agent_config in self.DEFAULT_AGENTS:
            try:
                # Check if agent already exists
                existing_agents = await self.registry.get_agents_by_type(agent_config["agent_type"])
                if any(agent.name == agent_config["name"] for agent in existing_agents):
                    logger.info(f"Agent {agent_config['name']} already exists, skipping")
                    continue
                
                # Create registration request
                request = AgentRegistrationRequest(**agent_config)
                
                # Create agent instance
                agent_instance = self._create_agent_instance(request)
                
                # Register in Redis
                from .models import AgentMetadata, AgentStatus
                agent_metadata = AgentMetadata(
                    name=request.name,
                    agent_type=request.agent_type,
                    capabilities=request.capabilities,
                    config=request.config,
                    max_concurrent_tasks=request.max_concurrent_tasks,
                    status=AgentStatus.IDLE
                )
                
                success = await self.registry.register_agent(agent_metadata)
                if success:
                    self.agent_instances[agent_metadata.agent_id] = agent_instance
                    logger.info(f"Bootstrapped agent: {request.name}")
                else:
                    logger.error(f"Failed to register agent: {request.name}")
                    
            except Exception as e:
                logger.error(f"Failed to bootstrap agent {agent_config['name']}: {str(e)}")
        
        logger.info(f"Bootstrap complete. {len(self.agent_instances)} agents ready.")
        return self.agent_instances
    
    def _create_agent_instance(self, request: AgentRegistrationRequest):
        """Create agent instance based on type."""
        if request.agent_type == "text_processor":
            return TextProcessingAgent(request.name, request.config)
        elif request.agent_type == "data_analyzer":
            return DataAnalysisAgent(request.name, request.config)
        else:
            raise ValueError(f"Unknown agent type: {request.agent_type}")
    
    async def recover_agent_instances(self) -> Dict[str, object]:
        """Recover agent instances from Redis on service restart."""
        logger.info("Recovering agent instances from Redis...")
        
        try:
            # Get all active agents from Redis
            stats = await self.registry.get_registry_stats()
            recovered_instances = {}
            
            for agent_type in stats.get("agents_by_type", {}):
                agents = await self.registry.get_agents_by_type(agent_type)
                
                for agent in agents:
                    try:
                        # Create agent instance
                        request = AgentRegistrationRequest(
                            name=agent.name,
                            agent_type=agent.agent_type,
                            capabilities=agent.capabilities,
                            config=agent.config,
                            max_concurrent_tasks=agent.max_concurrent_tasks
                        )
                        
                        agent_instance = self._create_agent_instance(request)
                        recovered_instances[agent.agent_id] = agent_instance
                        
                    except Exception as e:
                        logger.error(f"Failed to recover agent {agent.name}: {str(e)}")
                        # Remove broken agent from Redis
                        await self.registry.unregister_agent(agent.agent_id)
            
            logger.info(f"Recovered {len(recovered_instances)} agent instances")
            self.agent_instances.update(recovered_instances)
            return self.agent_instances
            
        except Exception as e:
            logger.error(f"Agent recovery failed: {str(e)}")
            return {}
    
    def get_agent_instance(self, agent_id: str):
        """Get agent instance by ID."""
        return self.agent_instances.get(agent_id)
    
    def add_agent_instance(self, agent_id: str, agent_instance):
        """Add new agent instance."""
        self.agent_instances[agent_id] = agent_instance
    
    def remove_agent_instance(self, agent_id: str):
        """Remove agent instance."""
        return self.agent_instances.pop(agent_id, None)