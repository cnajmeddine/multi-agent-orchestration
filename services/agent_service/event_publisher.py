# services/agent_service/event_publisher.py
# Event publishing for agent service

import asyncio
import httpx
import logging
from typing import Dict, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

class AgentEventPublisher:
    """Publishes agent events to communication and monitoring services."""
    
    def __init__(self):
        self.communication_url = "http://localhost:8004"
        self.monitoring_url = "http://localhost:8003"
        self.http_client = httpx.AsyncClient(timeout=5.0)
    
    async def publish_agent_registered(self, agent_metadata):
        """Publish agent registration event."""
        event_data = {
            "event_type": "agent.registered",
            "source_service": "agent-service",
            "source_id": agent_metadata.agent_id,
            "priority": "medium",
            "payload": {
                "agent_name": agent_metadata.name,
                "agent_type": agent_metadata.agent_type,
                "capabilities": [cap.dict() for cap in agent_metadata.capabilities],
                "max_concurrent_tasks": agent_metadata.max_concurrent_tasks
            },
            "metadata": {
                "agent_id": agent_metadata.agent_id,
                "timestamp": datetime.utcnow().isoformat()
            }
        }
        
        await self._send_to_communication(event_data)
        await self._send_counter_to_monitoring("agents_registered", 1)
    
    async def publish_agent_unregistered(self, agent_id: str):
        """Publish agent unregistration event."""
        event_data = {
            "event_type": "agent.unregistered", 
            "source_service": "agent-service",
            "source_id": agent_id,
            "priority": "medium",
            "payload": {"agent_id": agent_id},
            "metadata": {
                "agent_id": agent_id,
                "timestamp": datetime.utcnow().isoformat()
            }
        }
        
        await self._send_to_communication(event_data)
        await self._send_counter_to_monitoring("agents_unregistered", 1)
    
    async def publish_task_executed(self, agent_id: str, task_id: str, 
                                  execution_time: float, success: bool,
                                  error_message: str = None):
        """Publish task execution event."""
        event_type = "agent.task_completed" if success else "agent.task_failed"
        
        event_data = {
            "event_type": event_type,
            "source_service": "agent-service", 
            "source_id": agent_id,
            "priority": "high" if not success else "low",
            "payload": {
                "task_id": task_id,
                "execution_time": execution_time,
                "success": success,
                "error_message": error_message
            },
            "metadata": {
                "agent_id": agent_id,
                "timestamp": datetime.utcnow().isoformat()
            }
        }
        
        await self._send_to_communication(event_data)
        
        # Send metrics to monitoring
        await self._send_metric_to_monitoring("agent_response_time", execution_time, {"agent_id": agent_id})
        await self._send_counter_to_monitoring("agent_tasks_executed", 1)
        
        if not success:
            await self._send_counter_to_monitoring("agent_tasks_failed", 1)
    
    async def publish_health_status(self, agent_id: str, status: str, 
                                  current_load: int, max_tasks: int):
        """Publish agent health status."""
        event_data = {
            "event_type": "agent.health_updated",
            "source_service": "agent-service",
            "source_id": agent_id, 
            "priority": "low",
            "payload": {
                "status": status,
                "current_load": current_load,
                "max_concurrent_tasks": max_tasks,
                "load_percentage": (current_load / max_tasks * 100) if max_tasks > 0 else 0
            },
            "metadata": {
                "agent_id": agent_id,
                "timestamp": datetime.utcnow().isoformat()
            }
        }
        
        await self._send_to_communication(event_data)
        
        # Send load metrics
        await self._send_metric_to_monitoring("agent_load", current_load, {"agent_id": agent_id})
    
    async def _send_to_communication(self, event_data: Dict[str, Any]):
        """Send event to communication service."""
        try:
            response = await self.http_client.post(
                f"{self.communication_url}/events/publish",
                json=event_data
            )
            response.raise_for_status()
            
        except Exception as e:
            logger.warning(f"Failed to send event to communication service: {str(e)}")
    
    async def _send_metric_to_monitoring(self, metric_name: str, value: float, 
                                       labels: Dict[str, str] = None):
        """Send metric to monitoring service."""
        try:
            params = {"metric_name": metric_name, "value": value}
            if labels:
                params["labels"] = labels
            
            response = await self.http_client.post(
                f"{self.monitoring_url}/metrics/record",
                params=params
            )
            response.raise_for_status()
            
        except Exception as e:
            logger.warning(f"Failed to send metric to monitoring: {str(e)}")
    
    async def _send_counter_to_monitoring(self, counter_name: str, increment: int = 1):
        """Send counter increment to monitoring service."""
        try:
            response = await self.http_client.post(
                f"{self.monitoring_url}/counters/increment",
                params={"counter_name": counter_name, "increment": increment}
            )
            response.raise_for_status()
            
        except Exception as e:
            logger.warning(f"Failed to send counter to monitoring: {str(e)}")
    
    async def close(self):
        """Close HTTP client."""
        await self.http_client.aclose()

event_publisher = AgentEventPublisher()