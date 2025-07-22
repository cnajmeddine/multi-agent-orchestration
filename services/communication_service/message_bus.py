# Handles the internal message bus for inter-service and intra-service communication. 
# services/communication_service/message_bus.py
"""Redis Streams-based message bus for reliable event streaming."""

import redis
import json
import asyncio
import logging
from typing import Dict, List, Optional, Any, Callable, AsyncGenerator
from datetime import datetime, timedelta
import uuid

from .models import Event, EventType, StreamInfo
from .config import settings

logger = logging.getLogger(__name__)

class MessageBus:
    """Redis Streams-based message bus for reliable event streaming."""
    
    def __init__(self):
        self.redis_client = redis.Redis(
            host=settings.redis_host,
            port=settings.redis_port,
            db=settings.redis_db,
            password=settings.redis_password,
            decode_responses=True
        )
        self.consumers: Dict[str, asyncio.Task] = {}
        self.running = False
        
    async def start(self):
        """Start the message bus."""
        try:
            # Test Redis connection
            self.redis_client.ping()
            self.running = True
            logger.info("Message bus started successfully")
        except Exception as e:
            logger.error(f"Failed to start message bus: {str(e)}")
            raise
    
    async def stop(self):
        """Stop the message bus and cleanup consumers."""
        self.running = False
        
        # Cancel all consumers
        for consumer_name, task in self.consumers.items():
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                logger.info(f"Consumer {consumer_name} cancelled")
        
        self.consumers.clear()
        logger.info("Message bus stopped")
    
    async def publish_event(self, event: Event) -> str:
        """Publish an event to the appropriate stream."""
        try:
            stream_name = self._get_stream_name(event.event_type)
            
            # Prepare event data for Redis
            event_data = {
                "event_id": event.event_id,
                "event_type": event.event_type.value,
                "source_service": event.source_service,
                "source_id": event.source_id,
                "priority": event.priority.value,
                "payload": json.dumps(event.payload),
                "metadata": json.dumps(event.metadata),
                "timestamp": event.timestamp.isoformat(),
                "correlation_id": event.correlation_id or "",
                "retry_count": str(event.retry_count)
            }
            
            # Add to stream with automatic ID generation
            message_id = self.redis_client.xadd(stream_name, event_data)
            
            # Trim stream to keep within retention limits
            await self._trim_stream(stream_name)
            
            logger.info(f"Published event {event.event_id} to stream {stream_name} with ID {message_id}")
            return message_id
            
        except Exception as e:
            logger.error(f"Failed to publish event {event.event_id}: {str(e)}")
            raise
    
    async def subscribe_to_events(
        self, 
        event_types: List[EventType],
        consumer_group: str,
        consumer_name: str,
        handler: Callable[[Event], Any]
    ) -> str:
        """Subscribe to specific event types with a consumer group."""
        try:
            consumer_id = f"{consumer_group}:{consumer_name}"
            
            if consumer_id in self.consumers:
                raise ValueError(f"Consumer {consumer_id} already exists")
            
            # Create consumer task
            task = asyncio.create_task(
                self._event_consumer_loop(
                    event_types, consumer_group, consumer_name, handler
                )
            )
            
            self.consumers[consumer_id] = task
            logger.info(f"Created consumer {consumer_id} for events: {[et.value for et in event_types]}")
            
            return consumer_id
            
        except Exception as e:
            logger.error(f"Failed to create consumer {consumer_group}:{consumer_name}: {str(e)}")
            raise
    
    async def unsubscribe_consumer(self, consumer_id: str):
        """Unsubscribe a consumer."""
        try:
            if consumer_id in self.consumers:
                task = self.consumers[consumer_id]
                task.cancel()
                
                try:
                    await task
                except asyncio.CancelledError:
                    pass
                
                del self.consumers[consumer_id]
                logger.info(f"Unsubscribed consumer {consumer_id}")
            else:
                logger.warning(f"Consumer {consumer_id} not found")
                
        except Exception as e:
            logger.error(f"Failed to unsubscribe consumer {consumer_id}: {str(e)}")
    
    async def get_stream_info(self, event_type: EventType) -> StreamInfo:
        """Get information about a stream."""
        try:
            stream_name = self._get_stream_name(event_type)
            
            # Get stream info
            info = self.redis_client.xinfo_stream(stream_name)
            
            # Get consumer groups
            try:
                groups_info = self.redis_client.xinfo_groups(stream_name)
                groups = [group['name'] for group in groups_info]
            except redis.ResponseError:
                groups = []  # No groups exist yet
            
            return StreamInfo(
                stream_name=stream_name,
                length=info['length'],
                consumer_groups=groups,
                last_event_id=info.get('last-generated-id'),
                first_event_id=info.get('first-entry', {}).get('id') if info.get('first-entry') else None
            )
            
        except redis.ResponseError as e:
            if "no such key" in str(e).lower():
                # Stream doesn't exist yet
                return StreamInfo(stream_name=self._get_stream_name(event_type))
            raise
        except Exception as e:
            logger.error(f"Failed to get stream info for {event_type}: {str(e)}")
            raise
    
    async def get_pending_events(
        self, 
        event_type: EventType, 
        consumer_group: str,
        consumer_name: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get pending events for a consumer group."""
        try:
            stream_name = self._get_stream_name(event_type)
            
            if consumer_name:
                # Get pending for specific consumer
                pending = self.redis_client.xpending_range(
                    stream_name, consumer_group, "-", "+", 100, consumer_name
                )
            else:
                # Get all pending for group
                pending = self.redis_client.xpending_range(
                    stream_name, consumer_group, "-", "+", 100
                )
            
            return pending
            
        except Exception as e:
            logger.error(f"Failed to get pending events: {str(e)}")
            return []
    
    async def acknowledge_event(
        self, 
        event_type: EventType, 
        consumer_group: str, 
        message_id: str
    ):
        """Acknowledge processing of an event."""
        try:
            stream_name = self._get_stream_name(event_type)
            self.redis_client.xack(stream_name, consumer_group, message_id)
            logger.debug(f"Acknowledged event {message_id} in stream {stream_name}")
            
        except Exception as e:
            logger.error(f"Failed to acknowledge event {message_id}: {str(e)}")
    
    async def _event_consumer_loop(
        self,
        event_types: List[EventType],
        consumer_group: str,
        consumer_name: str,
        handler: Callable[[Event], Any]
    ):
        """Main consumer loop for processing events."""
        streams = {self._get_stream_name(et): ">" for et in event_types}
        
        # Create consumer groups if they don't exist
        for stream_name in streams.keys():
            try:
                self.redis_client.xgroup_create(stream_name, consumer_group, id="0", mkstream=True)
                logger.info(f"Created consumer group {consumer_group} for stream {stream_name}")
            except redis.ResponseError as e:
                if "BUSYGROUP" not in str(e):
                    logger.error(f"Failed to create consumer group: {str(e)}")
        
        logger.info(f"Starting consumer loop for {consumer_group}:{consumer_name}")
        
        while self.running:
            try:
                # Read from streams
                messages = self.redis_client.xreadgroup(
                    consumer_group,
                    consumer_name, 
                    streams,
                    count=settings.event_batch_size,
                    block=1000  # 1 second timeout
                )
                
                for stream_name, stream_messages in messages:
                    for message_id, fields in stream_messages:
                        try:
                            # Parse event from Redis data
                            event = self._parse_event_from_redis(fields)
                            
                            # Process event
                            await self._process_event(event, handler, stream_name, consumer_group, message_id)
                            
                        except Exception as e:
                            logger.error(f"Failed to process message {message_id}: {str(e)}")
                            # TODO: Send to dead letter queue
                
            except redis.ResponseError as e:
                if "NOGROUP" in str(e):
                    logger.warning(f"Consumer group {consumer_group} doesn't exist, recreating...")
                    continue
                else:
                    logger.error(f"Redis error in consumer loop: {str(e)}")
                    await asyncio.sleep(5)
            except Exception as e:
                logger.error(f"Unexpected error in consumer loop: {str(e)}")
                await asyncio.sleep(5)
    
    async def _process_event(
        self, 
        event: Event, 
        handler: Callable[[Event], Any],
        stream_name: str,
        consumer_group: str,
        message_id: str
    ):
        """Process a single event with error handling."""
        try:
            # Call the handler
            if asyncio.iscoroutinefunction(handler):
                await handler(event)
            else:
                handler(event)
            
            # Acknowledge successful processing
            await self.acknowledge_event(
                EventType(event.event_type), consumer_group, message_id
            )
            
            logger.debug(f"Successfully processed event {event.event_id}")
            
        except Exception as e:
            logger.error(f"Handler failed for event {event.event_id}: {str(e)}")
            
            # TODO: Implement retry logic and dead letter queue
            # For now, just acknowledge to prevent reprocessing
            await self.acknowledge_event(
                EventType(event.event_type), consumer_group, message_id
            )
    
    def _parse_event_from_redis(self, fields: Dict[str, str]) -> Event:
        """Parse an Event object from Redis stream data."""
        try:
            return Event(
                event_id=fields['event_id'],
                event_type=EventType(fields['event_type']),
                source_service=fields['source_service'],
                source_id=fields['source_id'],
                priority=fields['priority'],
                payload=json.loads(fields['payload']) if fields['payload'] else {},
                metadata=json.loads(fields['metadata']) if fields['metadata'] else {},
                timestamp=datetime.fromisoformat(fields['timestamp']),
                correlation_id=fields['correlation_id'] if fields['correlation_id'] else None,
                retry_count=int(fields['retry_count'])
            )
        except Exception as e:
            logger.error(f"Failed to parse event from Redis: {str(e)}")
            raise
    
    def _get_stream_name(self, event_type: EventType) -> str:
        """Generate stream name for an event type."""
        # Group related events into streams
        if event_type.value.startswith("workflow."):
            return f"{settings.stream_prefix}:workflows"
        elif event_type.value.startswith("step."):
            return f"{settings.stream_prefix}:steps"
        elif event_type.value.startswith("agent."):
            return f"{settings.stream_prefix}:agents"
        else:
            return f"{settings.stream_prefix}:system"
    
    async def _trim_stream(self, stream_name: str):
        """Trim stream to keep within retention limits."""
        try:
            # Calculate cutoff time
            cutoff_time = datetime.utcnow() - timedelta(hours=settings.message_retention_hours)
            cutoff_ms = int(cutoff_time.timestamp() * 1000)
            
            # Trim by time (approximately)
            self.redis_client.xtrim(stream_name, maxlen=10000, approximate=True)
            
        except Exception as e:
            logger.warning(f"Failed to trim stream {stream_name}: {str(e)}")
    
    async def cleanup_old_messages(self):
        """Cleanup old messages from all streams."""
        try:
            # Get all stream keys
            stream_keys = self.redis_client.keys(f"{settings.stream_prefix}:*")
            
            for stream_key in stream_keys:
                await self._trim_stream(stream_key)
            
            logger.info(f"Cleaned up {len(stream_keys)} streams")
            
        except Exception as e:
            logger.error(f"Failed to cleanup old messages: {str(e)}")