# base_agent.py - Abstract base class for agents
# This file defines the interface for all agent types.

from abc import ABC, abstractmethod
from typing import Dict, Any, List
import asyncio
import time
import logging
from datetime import datetime

from ..models import AgentCapability, AgentStatus, AgentRequest, AgentResponse

logger = logging.getLogger(__name__)

class BaseAgent(ABC):
    def __init__(self, name: str, agent_type: str, capabilities: List[AgentCapability], 
                 config: Dict[str, Any] = None):
        self.name = name
        self.agent_type = agent_type
        self.capabilities = capabilities
        self.config = config or {}
        self.status = AgentStatus.INITIALIZING
        self.current_load = 0
        self.max_concurrent_tasks = self.config.get('max_concurrent_tasks', 1)
        self._task_semaphore = asyncio.Semaphore(self.max_concurrent_tasks)
        
    @abstractmethod
    async def process_task(self, request: AgentRequest) -> AgentResponse:
        """Process a single task. Must be implemented by subclasses."""
        pass
    
    async def execute_request(self, request: AgentRequest) -> AgentResponse:
        """Main execution wrapper with error handling and load management."""
        start_time = time.time()
        
        async with self._task_semaphore:
            self.current_load += 1
            self.status = AgentStatus.BUSY
            
            try:
                logger.info(f"Agent {self.name} processing task {request.task_id}")
                response = await asyncio.wait_for(
                    self.process_task(request), 
                    timeout=request.timeout
                )
                response.execution_time = time.time() - start_time
                return response
                
            except asyncio.TimeoutError:
                logger.error(f"Task {request.task_id} timed out")
                return AgentResponse(
                    task_id=request.task_id,
                    agent_id=self.name,
                    success=False,
                    error_message=f"Task timed out after {request.timeout} seconds",
                    execution_time=time.time() - start_time
                )
            except Exception as e:
                logger.error(f"Task {request.task_id} failed: {str(e)}")
                return AgentResponse(
                    task_id=request.task_id,
                    agent_id=self.name,
                    success=False,
                    error_message=str(e),
                    execution_time=time.time() - start_time
                )
            finally:
                self.current_load -= 1
                self.status = AgentStatus.IDLE if self.current_load == 0 else AgentStatus.BUSY
    
    def get_health_status(self) -> Dict[str, Any]:
        """Return current health status."""
        return {
            "agent_id": self.name,
            "status": self.status.value,
            "current_load": self.current_load,
            "max_concurrent_tasks": self.max_concurrent_tasks,
            "capabilities": [cap.dict() for cap in self.capabilities]
        }