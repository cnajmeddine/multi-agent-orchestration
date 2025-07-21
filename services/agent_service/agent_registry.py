# agent_registry.py - Core agent management logic
# This file contains the logic for registering, retrieving, and managing agents.

import redis
import json
import asyncio
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import logging

from .models import AgentMetadata, AgentStatus, AgentHealthCheck
from .config import settings

logger = logging.getLogger(__name__)

class AgentRegistry:
    def __init__(self):
        self.redis_client = redis.Redis(
            host=settings.redis_host,
            port=settings.redis_port,
            db=settings.redis_db,
            password=settings.redis_password,
            decode_responses=True
        )
        
    async def register_agent(self, agent_metadata: AgentMetadata) -> bool:
        """Register a new agent in Redis."""
        try:
            # Store agent metadata as hash
            agent_key = f"agent:{agent_metadata.agent_id}"
            agent_data = agent_metadata.dict()
            agent_data['last_heartbeat'] = agent_data['last_heartbeat'].isoformat()
            agent_data['created_at'] = agent_data['created_at'].isoformat()

            # FIX: Store enum value, not string representation
            agent_data['status'] = agent_metadata.status.value
            
            # REDIS PATTERN 1: HASH for agent metadata
            self.redis_client.hset(agent_key, mapping={
                k: json.dumps(v) if isinstance(v, (dict, list)) else str(v) 
                for k, v in agent_data.items()
            })
            
            # REDIS PATTERN 2: SET for agent pools by type
            type_set_key = f"agents:type:{agent_metadata.agent_type}"
            self.redis_client.sadd(type_set_key, agent_metadata.agent_id)
            
            # REDIS PATTERN 3: SORTED SET for load balancing (score = current_load)
            load_key = f"agents:load:{agent_metadata.agent_type}"
            self.redis_client.zadd(load_key, {agent_metadata.agent_id: agent_metadata.current_load})
            
            # REDIS PATTERN 4: SET for all active agents
            self.redis_client.sadd("agents:active", agent_metadata.agent_id)
            
            # Set expiration for agent key (auto-cleanup if agent dies)
            self.redis_client.expire(agent_key, settings.agent_timeout)
            
            logger.info(f"Registered agent {agent_metadata.agent_id} of type {agent_metadata.agent_type}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to register agent {agent_metadata.agent_id}: {str(e)}")
            return False
    
    async def unregister_agent(self, agent_id: str) -> bool:
        """Remove agent from all Redis structures."""
        try:
            # Get agent info first
            agent_data = await self.get_agent(agent_id)
            if not agent_data:
                return False
            
            agent_type = agent_data.agent_type
            
            # Remove from all Redis structures
            self.redis_client.delete(f"agent:{agent_id}")
            self.redis_client.srem(f"agents:type:{agent_type}", agent_id)
            self.redis_client.zrem(f"agents:load:{agent_type}", agent_id)
            self.redis_client.srem("agents:active", agent_id)
            self.redis_client.hdel("heartbeats", agent_id)
            
            logger.info(f"Unregistered agent {agent_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to unregister agent {agent_id}: {str(e)}")
            return False
    
    async def get_agent(self, agent_id: str) -> Optional[AgentMetadata]:
        """Retrieve agent metadata from Redis."""
        try:
            agent_key = f"agent:{agent_id}"
            agent_data = self.redis_client.hgetall(agent_key)
            
            if not agent_data:
                return None
            
            # Convert Redis strings back to proper types
            parsed_data = {}
            for k, v in agent_data.items():
                if k in ['capabilities', 'config']:
                    parsed_data[k] = json.loads(v)
                elif k in ['current_load', 'max_concurrent_tasks']:
                    parsed_data[k] = int(v)
                elif k in ['last_heartbeat', 'created_at']:
                    parsed_data[k] = datetime.fromisoformat(v)
                elif k == 'status':
                    # FIX: Handle status enum properly
                    parsed_data[k] = v  # Store as string, Pydantic will convert
                else:
                    parsed_data[k] = v
            
            return AgentMetadata(**parsed_data)
            
        except Exception as e:
            logger.error(f"Failed to get agent {agent_id}: {str(e)}")
            return None
    
    async def get_agents_by_type(self, agent_type: str) -> List[AgentMetadata]:
        """Get all agents of a specific type."""
        try:
            type_set_key = f"agents:type:{agent_type}"
            agent_ids = self.redis_client.smembers(type_set_key)
            
            agents = []
            for agent_id in agent_ids:
                agent = await self.get_agent(agent_id)
                if agent and agent.status != AgentStatus.OFFLINE:
                    agents.append(agent)
            
            return agents
            
        except Exception as e:
            logger.error(f"Failed to get agents by type {agent_type}: {str(e)}")
            return []
    
    async def find_available_agent(self, agent_type: str) -> Optional[AgentMetadata]:
        """Find the least loaded available agent of a specific type."""
        try:
            load_key = f"agents:load:{agent_type}"
            
            # REDIS PATTERN: Get agent with lowest load using ZRANGE
            agent_ids_with_scores = self.redis_client.zrange(load_key, 0, -1, withscores=True)
            
            # If no agents in sorted set, fall back to type set
            if not agent_ids_with_scores:
                type_set_key = f"agents:type:{agent_type}"
                agent_ids = self.redis_client.smembers(type_set_key)
                agent_ids_with_scores = [(agent_id, 0) for agent_id in agent_ids]
            
            for agent_id, score in agent_ids_with_scores:
                agent = await self.get_agent(agent_id)
                if agent and agent.status in [AgentStatus.IDLE, AgentStatus.BUSY]:
                    if agent.current_load < agent.max_concurrent_tasks:
                        logger.info(f"Found available agent: {agent_id} (load: {agent.current_load})")
                        return agent
            
            logger.warning(f"No available agents found for type {agent_type}")
            return None
            
        except Exception as e:
            logger.error(f"Failed to find available agent of type {agent_type}: {str(e)}")
            return None
    
    async def update_agent_load(self, agent_id: str, new_load: int) -> bool:
        """Update agent's current load in Redis."""
        try:
            agent = await self.get_agent(agent_id)
            if not agent:
                return False
            
            # Update load in sorted set
            load_key = f"agents:load:{agent.agent_type}"
            self.redis_client.zadd(load_key, {agent_id: new_load})
            
            # Update in agent hash
            agent_key = f"agent:{agent_id}"
            self.redis_client.hset(agent_key, "current_load", new_load)
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to update load for agent {agent_id}: {str(e)}")
            return False
    
    async def heartbeat(self, agent_id: str, health_data: AgentHealthCheck) -> bool:
        """Update agent heartbeat and health status."""
        try:
            # REDIS PATTERN: HASH for heartbeats with timestamp
            self.redis_client.hset("heartbeats", agent_id, datetime.utcnow().isoformat())
            
            # Update agent status and load - FIX enum serialization
            agent_key = f"agent:{agent_id}"
            self.redis_client.hset(agent_key, mapping={
                "status": health_data.status.value,  # This is correct
                "current_load": health_data.current_load,
                "last_heartbeat": health_data.timestamp.isoformat()
            })
            
            # Update load in sorted set
            agent = await self.get_agent(agent_id)
            if agent:
                load_key = f"agents:load:{agent.agent_type}"
                self.redis_client.zadd(load_key, {agent_id: health_data.current_load})
            
            # Refresh expiration
            self.redis_client.expire(agent_key, settings.agent_timeout)
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to update heartbeat for agent {agent_id}: {str(e)}")
            return False
    
    async def cleanup_dead_agents(self) -> int:
        """Remove agents that haven't sent heartbeat recently."""
        try:
            cutoff_time = datetime.utcnow() - timedelta(seconds=settings.agent_timeout)
            heartbeats = self.redis_client.hgetall("heartbeats")
            
            dead_agents = []
            for agent_id, heartbeat_str in heartbeats.items():
                try:
                    last_heartbeat = datetime.fromisoformat(heartbeat_str)
                    if last_heartbeat < cutoff_time:
                        dead_agents.append(agent_id)
                except ValueError:
                    dead_agents.append(agent_id)  # Invalid timestamp
            
            # Remove dead agents
            for agent_id in dead_agents:
                await self.unregister_agent(agent_id)
            
            logger.info(f"Cleaned up {len(dead_agents)} dead agents")
            return len(dead_agents)
            
        except Exception as e:
            logger.error(f"Failed to cleanup dead agents: {str(e)}")
            return 0
    
    async def get_registry_stats(self) -> Dict[str, Any]:
        """Get overall registry statistics."""
        try:
            active_agents = self.redis_client.scard("agents:active")
            
            # Get agent counts by type
            agent_types = {}
            for agent_id in self.redis_client.smembers("agents:active"):
                agent = await self.get_agent(agent_id)
                if agent:
                    agent_types[agent.agent_type] = agent_types.get(agent.agent_type, 0) + 1
            
            return {
                "total_active_agents": active_agents,
                "agents_by_type": agent_types,
                "heartbeat_count": self.redis_client.hlen("heartbeats")
            }
            
        except Exception as e:
            logger.error(f"Failed to get registry stats: {str(e)}")
            return {}