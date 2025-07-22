# Publishes events to subscribers and external systems from the communication service. 
# services/communication_service/event_publisher.py
"""Event publisher for workflow state changes and system events."""

import asyncio
import logging
from typing import Dict, List, Optional, Any, Set
from datetime import datetime
import uuid

from .models import Event, EventType, EventPriority
from .message_bus import MessageBus
from .config import settings

logger = logging.getLogger(__name__)

class EventPublisher:
    """Publishes and manages workflow and system events."""
    
    def __init__(self, message_bus: MessageBus):
        self.message_bus = message_bus
        self.subscribers: Dict[str, Set[str]] = {}  # event_type -> set of subscriber_ids
        self.event_handlers: Dict[str, callable] = {}  # subscriber_id -> handler function
        self.running = False
        
    async def start(self):
        """Start the event publisher."""
        self.running = True
        logger.info("Event publisher started")
    
    async def stop(self):
        """Stop the event publisher."""
        self.running = False
        logger.info("Event publisher stopped")
    
    async def publish_workflow_event(
        self,
        event_type: EventType,
        workflow_id: str,
        execution_id: Optional[str] = None,
        step_id: Optional[str] = None,
        payload: Optional[Dict[str, Any]] = None,
        priority: EventPriority = EventPriority.MEDIUM,
        correlation_id: Optional[str] = None
    ) -> str:
        """Publish a workflow-related event."""
        try:
            event = Event(
                event_type=event_type,
                source_service="workflow-service",
                source_id=execution_id or workflow_id,
                priority=priority,
                payload=payload or {},
                metadata={
                    "workflow_id": workflow_id,
                    "execution_id": execution_id,
                    "step_id": step_id
                },
                correlation_id=correlation_id
            )
            
            # Add standard workflow metadata
            event.payload.update({
                "workflow_id": workflow_id,
                "execution_id": execution_id,
                "timestamp": datetime.utcnow().isoformat()
            })
            
            if step_id:
                event.payload["step_id"] = step_id
            
            message_id = await self.message_bus.publish_event(event)
            
            logger.info(f"Published workflow event {event_type.value} for workflow {workflow_id}")
            return event.event_id
            
        except Exception as e:
            logger.error(f"Failed to publish workflow event: {str(e)}")
            raise
    
    async def publish_agent_event(
        self,
        event_type: EventType,
        agent_id: str,
        agent_type: Optional[str] = None,
        payload: Optional[Dict[str, Any]] = None,
        priority: EventPriority = EventPriority.MEDIUM
    ) -> str:
        """Publish an agent-related event."""
        try:
            event = Event(
                event_type=event_type,
                source_service="agent-service",
                source_id=agent_id,
                priority=priority,
                payload=payload or {},
                metadata={
                    "agent_id": agent_id,
                    "agent_type": agent_type
                }
            )
            
            # Add standard agent metadata
            event.payload.update({
                "agent_id": agent_id,
                "agent_type": agent_type,
                "timestamp": datetime.utcnow().isoformat()
            })
            
            message_id = await self.message_bus.publish_event(event)
            
            logger.info(f"Published agent event {event_type.value} for agent {agent_id}")
            return event.event_id
            
        except Exception as e:
            logger.error(f"Failed to publish agent event: {str(e)}")
            raise
    
    async def publish_system_event(
        self,
        event_type: EventType,
        source_service: str,
        source_id: str,
        payload: Optional[Dict[str, Any]] = None,
        priority: EventPriority = EventPriority.HIGH,
        correlation_id: Optional[str] = None
    ) -> str:
        """Publish a system-level event."""
        try:
            event = Event(
                event_type=event_type,
                source_service=source_service,
                source_id=source_id,
                priority=priority,
                payload=payload or {},
                correlation_id=correlation_id
            )
            
            # Add standard system metadata
            event.payload.update({
                "source_service": source_service,
                "source_id": source_id,
                "timestamp": datetime.utcnow().isoformat()
            })
            
            message_id = await self.message_bus.publish_event(event)
            
            logger.info(f"Published system event {event_type.value} from {source_service}")
            return event.event_id
            
        except Exception as e:
            logger.error(f"Failed to publish system event: {str(e)}")
            raise
    
    async def publish_custom_event(
        self,
        event_type: EventType,
        source_service: str,
        source_id: str,
        payload: Dict[str, Any],
        priority: EventPriority = EventPriority.MEDIUM,
        metadata: Optional[Dict[str, Any]] = None,
        correlation_id: Optional[str] = None
    ) -> str:
        """Publish a custom event with full control over all fields."""
        try:
            event = Event(
                event_type=event_type,
                source_service=source_service,
                source_id=source_id,
                priority=priority,
                payload=payload,
                metadata=metadata or {},
                correlation_id=correlation_id
            )
            
            message_id = await self.message_bus.publish_event(event)
            
            logger.info(f"Published custom event {event_type.value}")
            return event.event_id
            
        except Exception as e:
            logger.error(f"Failed to publish custom event: {str(e)}")
            raise
    
    async def subscribe_to_events(
        self,
        event_types: List[EventType],
        handler_name: str,
        handler_function: callable,
        consumer_group: Optional[str] = None
    ) -> str:
        """Subscribe to specific event types with a handler function."""
        try:
            subscriber_id = f"{handler_name}_{uuid.uuid4().hex[:8]}"
            group = consumer_group or f"{settings.consumer_group_prefix}_{handler_name}"
            
            # Store handler
            self.event_handlers[subscriber_id] = handler_function
            
            # Track subscriptions
            for event_type in event_types:
                if event_type.value not in self.subscribers:
                    self.subscribers[event_type.value] = set()
                self.subscribers[event_type.value].add(subscriber_id)
            
            # Create message bus subscription
            consumer_id = await self.message_bus.subscribe_to_events(
                event_types, group, subscriber_id, self._handle_event_wrapper(subscriber_id)
            )
            
            logger.info(f"Created subscription {subscriber_id} for events: {[et.value for et in event_types]}")
            return subscriber_id
            
        except Exception as e:
            logger.error(f"Failed to create subscription: {str(e)}")
            raise
    
    async def unsubscribe_from_events(self, subscriber_id: str):
        """Unsubscribe from events."""
        try:
            # Remove from message bus
            await self.message_bus.unsubscribe_consumer(subscriber_id)
            
            # Clean up local tracking
            if subscriber_id in self.event_handlers:
                del self.event_handlers[subscriber_id]
            
            # Remove from subscribers tracking
            for event_type, subscribers in self.subscribers.items():
                subscribers.discard(subscriber_id)
            
            logger.info(f"Unsubscribed {subscriber_id}")
            
        except Exception as e:
            logger.error(f"Failed to unsubscribe {subscriber_id}: {str(e)}")
    
    def _handle_event_wrapper(self, subscriber_id: str):
        """Create a wrapper function for event handling."""
        async def wrapper(event: Event):
            try:
                handler = self.event_handlers.get(subscriber_id)
                if handler:
                    if asyncio.iscoroutinefunction(handler):
                        await handler(event)
                    else:
                        handler(event)
                else:
                    logger.warning(f"No handler found for subscriber {subscriber_id}")
            except Exception as e:
                logger.error(f"Event handler failed for {subscriber_id}: {str(e)}")
                # Don't re-raise to prevent message bus issues
        
        return wrapper
    
    async def get_event_stats(self) -> Dict[str, Any]:
        """Get statistics about event publishing and subscriptions."""
        try:
            stats = {
                "active_subscriptions": len(self.event_handlers),
                "event_type_subscriptions": {
                    event_type: len(subscribers) 
                    for event_type, subscribers in self.subscribers.items()
                },
                "stream_info": {}
            }
            
            # Get stream information for each event type
            for event_type in EventType:
                try:
                    stream_info = await self.message_bus.get_stream_info(event_type)
                    stats["stream_info"][event_type.value] = {
                        "length": stream_info.length,
                        "consumer_groups": len(stream_info.consumer_groups),
                        "last_event_id": stream_info.last_event_id
                    }
                except Exception as e:
                    logger.warning(f"Failed to get stream info for {event_type}: {str(e)}")
            
            return stats
            
        except Exception as e:
            logger.error(f"Failed to get event stats: {str(e)}")
            return {}
    
    async def replay_events(
        self,
        event_types: List[EventType],
        start_time: datetime,
        end_time: Optional[datetime] = None,
        handler: callable = None
    ) -> List[Event]:
        """Replay events from a specific time range."""
        # TODO: Implement event replay functionality
        # This would read from Redis streams within a time range
        # and optionally apply a handler function to each event
        logger.warning("Event replay not yet implemented")
        return []
    
    async def get_event_history(
        self,
        event_type: EventType,
        source_id: Optional[str] = None,
        limit: int = 100
    ) -> List[Event]:
        """Get recent event history for debugging/monitoring."""
        # TODO: Implement event history retrieval
        # This would read recent events from Redis streams
        logger.warning("Event history retrieval not yet implemented")
        return []