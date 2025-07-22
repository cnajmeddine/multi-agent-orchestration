# API endpoints for event publishing, subscription, and management. 
# services/communication_service/routes/events.py
"""API routes for event publishing and subscription."""

from fastapi import APIRouter, HTTPException, Depends, Request, BackgroundTasks
from typing import List, Optional, Dict, Any
import logging

from ..models import (
    EventPublishRequest, Event, EventType, StreamInfo,
    EventPriority
)
from ..event_publisher import EventPublisher
from ..message_bus import MessageBus

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/events", tags=["events"])

def get_event_publisher(request: Request) -> EventPublisher:
    """Get event publisher from app state."""
    if not hasattr(request.app.state, 'event_publisher'):
        raise HTTPException(status_code=500, detail="Event publisher not initialized")
    return request.app.state.event_publisher

def get_message_bus(request: Request) -> MessageBus:
    """Get message bus from app state."""
    if not hasattr(request.app.state, 'message_bus'):
        raise HTTPException(status_code=500, detail="Message bus not initialized")
    return request.app.state.message_bus

@router.post("/publish", response_model=Dict[str, str])
async def publish_event(
    request: EventPublishRequest,
    event_publisher: EventPublisher = Depends(get_event_publisher)
):
    """Publish an event to the message bus."""
    try:
        event_id = await event_publisher.publish_custom_event(
            event_type=request.event_type,
            source_service=request.source_service,
            source_id=request.source_id,
            priority=request.priority,
            payload=request.payload,
            metadata=request.metadata,
            correlation_id=request.correlation_id
        )
        
        return {"event_id": event_id, "status": "published"}
        
    except Exception as e:
        logger.error(f"Failed to publish event: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/publish/workflow")
async def publish_workflow_event(
    event_type: EventType,
    workflow_id: str,
    execution_id: Optional[str] = None,
    step_id: Optional[str] = None,
    payload: Optional[Dict[str, Any]] = None,
    priority: EventPriority = EventPriority.MEDIUM,
    correlation_id: Optional[str] = None,
    event_publisher: EventPublisher = Depends(get_event_publisher)
):
    """Publish a workflow-related event."""
    try:
        event_id = await event_publisher.publish_workflow_event(
            event_type=event_type,
            workflow_id=workflow_id,
            execution_id=execution_id,
            step_id=step_id,
            payload=payload,
            priority=priority,
            correlation_id=correlation_id
        )
        
        return {"event_id": event_id, "status": "published"}
        
    except Exception as e:
        logger.error(f"Failed to publish workflow event: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/publish/agent")
async def publish_agent_event(
    event_type: EventType,
    agent_id: str,
    agent_type: Optional[str] = None,
    payload: Optional[Dict[str, Any]] = None,
    priority: EventPriority = EventPriority.MEDIUM,
    event_publisher: EventPublisher = Depends(get_event_publisher)
):
    """Publish an agent-related event."""
    try:
        event_id = await event_publisher.publish_agent_event(
            event_type=event_type,
            agent_id=agent_id,
            agent_type=agent_type,
            payload=payload,
            priority=priority
        )
        
        return {"event_id": event_id, "status": "published"}
        
    except Exception as e:
        logger.error(f"Failed to publish agent event: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/subscribe")
async def subscribe_to_events(
    event_types: List[EventType],
    consumer_group: str,
    consumer_name: str,
    background_tasks: BackgroundTasks,
    message_bus: MessageBus = Depends(get_message_bus)
):
    """Subscribe to events with a consumer group."""
    try:
        # Simple event handler for testing
        def test_handler(event: Event):
            logger.info(f"Received event: {event.event_type.value} from {event.source_service}")
        
        consumer_id = await message_bus.subscribe_to_events(
            event_types=event_types,
            consumer_group=consumer_group,
            consumer_name=consumer_name,
            handler=test_handler
        )
        
        return {
            "consumer_id": consumer_id,
            "status": "subscribed",
            "event_types": [et.value for et in event_types]
        }
        
    except Exception as e:
        logger.error(f"Failed to subscribe to events: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/subscribe/{consumer_id}")
async def unsubscribe_from_events(
    consumer_id: str,
    message_bus: MessageBus = Depends(get_message_bus)
):
    """Unsubscribe from events."""
    try:
        await message_bus.unsubscribe_consumer(consumer_id)
        
        return {"consumer_id": consumer_id, "status": "unsubscribed"}
        
    except Exception as e:
        logger.error(f"Failed to unsubscribe consumer {consumer_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/streams", response_model=List[StreamInfo])
async def list_streams(
    message_bus: MessageBus = Depends(get_message_bus)
):
    """List all event streams."""
    try:
        streams = []
        
        for event_type in EventType:
            try:
                stream_info = await message_bus.get_stream_info(event_type)
                streams.append(stream_info)
            except Exception as e:
                logger.warning(f"Failed to get info for stream {event_type}: {str(e)}")
        
        return streams
        
    except Exception as e:
        logger.error(f"Failed to list streams: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/streams/{event_type}/info", response_model=StreamInfo)
async def get_stream_info(
    event_type: EventType,
    message_bus: MessageBus = Depends(get_message_bus)
):
    """Get information about a specific stream."""
    try:
        stream_info = await message_bus.get_stream_info(event_type)
        return stream_info
        
    except Exception as e:
        logger.error(f"Failed to get stream info for {event_type}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/streams/{event_type}/pending")
async def get_pending_events(
    event_type: EventType,
    consumer_group: str,
    consumer_name: Optional[str] = None,
    message_bus: MessageBus = Depends(get_message_bus)
):
    """Get pending events for a consumer group."""
    try:
        pending = await message_bus.get_pending_events(
            event_type=event_type,
            consumer_group=consumer_group,
            consumer_name=consumer_name
        )
        
        return {
            "event_type": event_type.value,
            "consumer_group": consumer_group,
            "consumer_name": consumer_name,
            "pending_count": len(pending),
            "pending_events": pending
        }
        
    except Exception as e:
        logger.error(f"Failed to get pending events: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/streams/{event_type}/acknowledge")
async def acknowledge_event(
    event_type: EventType,
    consumer_group: str,
    message_id: str,
    message_bus: MessageBus = Depends(get_message_bus)
):
    """Acknowledge processing of an event."""
    try:
        await message_bus.acknowledge_event(
            event_type=event_type,
            consumer_group=consumer_group,
            message_id=message_id
        )
        
        return {
            "message_id": message_id,
            "status": "acknowledged"
        }
        
    except Exception as e:
        logger.error(f"Failed to acknowledge event {message_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/stats")
async def get_event_stats(
    event_publisher: EventPublisher = Depends(get_event_publisher)
):
    """Get event publishing and subscription statistics."""
    try:
        stats = await event_publisher.get_event_stats()
        return stats
        
    except Exception as e:
        logger.error(f"Failed to get event stats: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/test")
async def publish_test_event(
    event_publisher: EventPublisher = Depends(get_event_publisher)
):
    """Publish a test event for debugging."""
    try:
        event_id = await event_publisher.publish_system_event(
            event_type=EventType.SYSTEM_ALERT,
            source_service="communication-service",
            source_id="test",
            payload={"message": "This is a test event", "test": True},
            priority=EventPriority.LOW
        )
        
        return {
            "event_id": event_id,
            "status": "test event published",
            "message": "Check streams and webhook deliveries"
        }
        
    except Exception as e:
        logger.error(f"Failed to publish test event: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))