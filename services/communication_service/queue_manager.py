# Manages message queues for asynchronous communication and task distribution. 
# services/communication_service/queue_manager.py
"""Message queue manager for async operations and dead letter queues."""

import redis
import json
import asyncio
import logging
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime, timedelta
import uuid

from .models import Message, MessageStatus, QueueStats, MessageEnqueueRequest
from .config import settings

logger = logging.getLogger(__name__)

class QueueManager:
    """Manages message queues for async operations with dead letter queue support."""
    
    def __init__(self):
        self.redis_client = redis.Redis(
            host=settings.redis_host,
            port=settings.redis_port,
            db=settings.redis_db,
            password=settings.redis_password,
            decode_responses=True
        )
        self.processors: Dict[str, asyncio.Task] = {}
        self.queue_handlers: Dict[str, Callable] = {}
        self.running = False
        
    async def start(self):
        """Start the queue manager."""
        try:
            # Test Redis connection
            self.redis_client.ping()
            self.running = True
            logger.info("Queue manager started successfully")
        except Exception as e:
            logger.error(f"Failed to start queue manager: {str(e)}")
            raise
    
    async def stop(self):
        """Stop the queue manager and cleanup processors."""
        self.running = False
        
        # Cancel all processors
        for queue_name, task in self.processors.items():
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                logger.info(f"Queue processor {queue_name} cancelled")
        
        self.processors.clear()
        logger.info("Queue manager stopped")
    
    async def enqueue_message(self, request: MessageEnqueueRequest) -> str:
        """Enqueue a message for processing."""
        try:
            message = Message(
                queue_name=request.queue_name,
                payload=request.payload,
                priority=request.priority,
                max_retries=request.max_retries
            )
            
            # Set scheduled time if delay specified
            if request.delay_seconds > 0:
                message.scheduled_at = datetime.utcnow() + timedelta(seconds=request.delay_seconds)
            
            # Store message in Redis
            await self._store_message(message)
            
            # Add to queue (use priority score for sorting)
            queue_key = self._get_queue_key(request.queue_name)
            score = self._calculate_priority_score(message)
            
            self.redis_client.zadd(queue_key, {message.message_id: score})
            
            logger.info(f"Enqueued message {message.message_id} to queue {request.queue_name}")
            return message.message_id
            
        except Exception as e:
            logger.error(f"Failed to enqueue message: {str(e)}")
            raise
    
    async def register_queue_handler(
        self, 
        queue_name: str, 
        handler: Callable[[Message], Any],
        max_concurrent: int = 1
    ):
        """Register a handler for a specific queue."""
        try:
            if queue_name in self.processors:
                raise ValueError(f"Queue {queue_name} already has a processor")
            
            # Store handler
            self.queue_handlers[queue_name] = handler
            
            # Start processor
            processor = asyncio.create_task(
                self._queue_processor(queue_name, handler, max_concurrent)
            )
            self.processors[queue_name] = processor
            
            logger.info(f"Registered handler for queue {queue_name} with concurrency {max_concurrent}")
            
        except Exception as e:
            logger.error(f"Failed to register queue handler for {queue_name}: {str(e)}")
            raise
    
    async def unregister_queue_handler(self, queue_name: str):
        """Unregister a queue handler."""
        try:
            if queue_name in self.processors:
                task = self.processors[queue_name]
                task.cancel()
                
                try:
                    await task
                except asyncio.CancelledError:
                    pass
                
                del self.processors[queue_name]
            
            if queue_name in self.queue_handlers:
                del self.queue_handlers[queue_name]
            
            logger.info(f"Unregistered handler for queue {queue_name}")
            
        except Exception as e:
            logger.error(f"Failed to unregister queue handler for {queue_name}: {str(e)}")
    
    async def get_message(self, message_id: str) -> Optional[Message]:
        """Get a message by ID."""
        try:
            message_key = self._get_message_key(message_id)
            message_data = self.redis_client.hgetall(message_key)
            
            if not message_data:
                return None
            
            return self._parse_message_from_redis(message_data)
            
        except Exception as e:
            logger.error(f"Failed to get message {message_id}: {str(e)}")
            return None
    
    async def get_queue_stats(self, queue_name: str) -> QueueStats:
        """Get statistics for a queue."""
        try:
            # Get queue contents
            queue_key = self._get_queue_key(queue_name)
            processing_key = self._get_processing_key(queue_name)
            dlq_key = self._get_dlq_key(queue_name)
            
            pending_count = self.redis_client.zcard(queue_key)
            processing_count = self.redis_client.zcard(processing_key)
            dlq_count = self.redis_client.zcard(dlq_key)
            
            # Calculate stats from message statuses
            completed_count = 0
            failed_count = 0
            total_processing_time = 0
            processed_messages = 0
            
            # Sample recent messages for timing stats
            recent_messages = self.redis_client.zrange(
                self._get_completed_key(queue_name), 0, 99, withscores=True
            )
            
            for message_id, _ in recent_messages:
                message = await self.get_message(message_id)
                if message and message.processed_at and message.created_at:
                    processing_time = (message.processed_at - message.created_at).total_seconds()
                    total_processing_time += processing_time
                    processed_messages += 1
                    
                    if message.status == MessageStatus.COMPLETED:
                        completed_count += 1
                    elif message.status == MessageStatus.FAILED:
                        failed_count += 1
            
            avg_processing_time = (
                total_processing_time / processed_messages 
                if processed_messages > 0 else 0.0
            )
            
            return QueueStats(
                queue_name=queue_name,
                pending_messages=pending_count,
                processing_messages=processing_count,
                completed_messages=completed_count,
                failed_messages=failed_count,
                dead_letter_messages=dlq_count,
                average_processing_time=avg_processing_time
            )
            
        except Exception as e:
            logger.error(f"Failed to get queue stats for {queue_name}: {str(e)}")
            return QueueStats(queue_name=queue_name)
    
    async def get_all_queue_stats(self) -> List[QueueStats]:
        """Get statistics for all queues."""
        try:
            # Find all queue keys
            queue_keys = self.redis_client.keys("queue:*")
            queue_names = [key.split(":", 1)[1] for key in queue_keys]
            
            stats = []
            for queue_name in queue_names:
                if not queue_name.startswith(("processing:", "completed:", "dlq:")):
                    queue_stats = await self.get_queue_stats(queue_name)
                    stats.append(queue_stats)
            
            return stats
            
        except Exception as e:
            logger.error(f"Failed to get all queue stats: {str(e)}")
            return []
    
    async def requeue_dead_letter_messages(self, queue_name: str, limit: int = 10) -> int:
        """Requeue messages from dead letter queue."""
        try:
            dlq_key = self._get_dlq_key(queue_name)
            queue_key = self._get_queue_key(queue_name)
            
            # Get messages from DLQ
            message_ids = self.redis_client.zrange(dlq_key, 0, limit - 1)
            requeued_count = 0
            
            for message_id in message_ids:
                message = await self.get_message(message_id)
                if message:
                    # Reset message status and retry count
                    message.status = MessageStatus.PENDING
                    message.retry_count = 0
                    message.error_message = None
                    
                    # Update message in Redis
                    await self._store_message(message)
                    
                    # Move back to main queue
                    score = self._calculate_priority_score(message)
                    self.redis_client.zadd(queue_key, {message_id: score})
                    self.redis_client.zrem(dlq_key, message_id)
                    
                    requeued_count += 1
                    logger.info(f"Requeued message {message_id} from DLQ")
            
            return requeued_count
            
        except Exception as e:
            logger.error(f"Failed to requeue DLQ messages for {queue_name}: {str(e)}")
            return 0
    
    async def purge_queue(self, queue_name: str) -> int:
        """Purge all messages from a queue."""
        try:
            queue_key = self._get_queue_key(queue_name)
            processing_key = self._get_processing_key(queue_name)
            
            # Get all message IDs
            queue_messages = self.redis_client.zrange(queue_key, 0, -1)
            processing_messages = self.redis_client.zrange(processing_key, 0, -1)
            all_messages = set(queue_messages + processing_messages)
            
            # Delete message data
            for message_id in all_messages:
                message_key = self._get_message_key(message_id)
                self.redis_client.delete(message_key)
            
            # Clear queues
            self.redis_client.delete(queue_key)
            self.redis_client.delete(processing_key)
            
            purged_count = len(all_messages)
            logger.info(f"Purged {purged_count} messages from queue {queue_name}")
            return purged_count
            
        except Exception as e:
            logger.error(f"Failed to purge queue {queue_name}: {str(e)}")
            return 0
    
    async def _queue_processor(self, queue_name: str, handler: Callable, max_concurrent: int):
        """Main queue processor loop."""
        logger.info(f"Starting queue processor for {queue_name} (concurrency: {max_concurrent})")
        
        semaphore = asyncio.Semaphore(max_concurrent)
        
        while self.running:
            try:
                # Get next message
                message = await self._dequeue_message(queue_name)
                
                if message:
                    # Process message with concurrency control
                    asyncio.create_task(
                        self._process_message_with_semaphore(message, handler, semaphore)
                    )
                else:
                    # No messages, wait before checking again
                    await asyncio.sleep(1)
                
            except Exception as e:
                logger.error(f"Queue processor error for {queue_name}: {str(e)}")
                await asyncio.sleep(5)
        
        logger.info(f"Queue processor for {queue_name} stopped")
    
    async def _process_message_with_semaphore(
        self, 
        message: Message, 
        handler: Callable, 
        semaphore: asyncio.Semaphore
    ):
        """Process message with concurrency control."""
        async with semaphore:
            await self._process_message(message, handler)
    
    async def _process_message(self, message: Message, handler: Callable):
        """Process a single message with error handling and retries."""
        try:
            # Update message status
            message.status = MessageStatus.PROCESSING
            await self._store_message(message)
            
            logger.debug(f"Processing message {message.message_id}")
            
            # Call handler
            if asyncio.iscoroutinefunction(handler):
                await handler(message)
            else:
                handler(message)
            
            # Mark as completed
            message.status = MessageStatus.COMPLETED
            message.processed_at = datetime.utcnow()
            await self._store_message(message)
            
            # Move to completed queue
            await self._move_to_completed(message)
            
            logger.debug(f"Message {message.message_id} processed successfully")
            
        except Exception as e:
            logger.error(f"Message {message.message_id} processing failed: {str(e)}")
            
            # Handle retry logic
            message.retry_count += 1
            message.error_message = str(e)
            
            if message.retry_count <= message.max_retries:
                # Retry: put back in queue with delay
                message.status = MessageStatus.PENDING
                message.scheduled_at = datetime.utcnow() + timedelta(
                    seconds=min(60, 2 ** message.retry_count)  # Exponential backoff, max 60s
                )
                await self._store_message(message)
                
                queue_key = self._get_queue_key(message.queue_name)
                score = self._calculate_priority_score(message)
                self.redis_client.zadd(queue_key, {message.message_id: score})
                
                logger.info(f"Message {message.message_id} requeued for retry {message.retry_count}")
                
            else:
                # Max retries exceeded, send to dead letter queue
                message.status = MessageStatus.DEAD_LETTER
                await self._store_message(message)
                await self._move_to_dlq(message)
                
                logger.error(f"Message {message.message_id} moved to DLQ after {message.retry_count} retries")
        
        finally:
            # Remove from processing queue
            processing_key = self._get_processing_key(message.queue_name)
            self.redis_client.zrem(processing_key, message.message_id)
    
    async def _dequeue_message(self, queue_name: str) -> Optional[Message]:
        """Dequeue the next message from a queue."""
        try:
            queue_key = self._get_queue_key(queue_name)
            processing_key = self._get_processing_key(queue_name)
            
            # Get highest priority message that's ready for processing
            current_time = datetime.utcnow().timestamp()
            
            # Use ZPOPMIN to atomically get and remove the highest priority message
            result = self.redis_client.zpopmin(queue_key, 1)
            
            if not result:
                return None
            
            message_id, score = result[0]
            message = await self.get_message(message_id)
            
            if not message:
                logger.warning(f"Message {message_id} not found")
                return None
            
            # Check if message is scheduled for future processing
            if message.scheduled_at and message.scheduled_at > datetime.utcnow():
                # Put back in queue
                self.redis_client.zadd(queue_key, {message_id: score})
                return None
            
            # Move to processing queue
            self.redis_client.zadd(processing_key, {message_id: current_time})
            
            return message
            
        except Exception as e:
            logger.error(f"Failed to dequeue message from {queue_name}: {str(e)}")
            return None
    
    async def _store_message(self, message: Message):
        """Store message data in Redis."""
        try:
            message_key = self._get_message_key(message.message_id)
            
            message_data = {
                "message_id": message.message_id,
                "queue_name": message.queue_name,
                "payload": json.dumps(message.payload),
                "priority": str(message.priority),
                "status": message.status.value,
                "created_at": message.created_at.isoformat(),
                "scheduled_at": message.scheduled_at.isoformat() if message.scheduled_at else "",
                "processed_at": message.processed_at.isoformat() if message.processed_at else "",
                "retry_count": str(message.retry_count),
                "max_retries": str(message.max_retries),
                "error_message": message.error_message or "",
                "processing_timeout": str(message.processing_timeout)
            }
            
            self.redis_client.hset(message_key, mapping=message_data)
            
            # Set expiration (keep completed/failed messages for 7 days)
            if message.status in [MessageStatus.COMPLETED, MessageStatus.FAILED, MessageStatus.DEAD_LETTER]:
                self.redis_client.expire(message_key, 7 * 24 * 3600)
            else:
                self.redis_client.expire(message_key, 24 * 3600)
            
        except Exception as e:
            logger.error(f"Failed to store message {message.message_id}: {str(e)}")
            raise
    
    def _parse_message_from_redis(self, data: Dict[str, str]) -> Message:
        """Parse a Message object from Redis data."""
        try:
            return Message(
                message_id=data['message_id'],
                queue_name=data['queue_name'],
                payload=json.loads(data['payload']),
                priority=int(data['priority']),
                status=MessageStatus(data['status']),
                created_at=datetime.fromisoformat(data['created_at']),
                scheduled_at=datetime.fromisoformat(data['scheduled_at']) if data['scheduled_at'] else None,
                processed_at=datetime.fromisoformat(data['processed_at']) if data['processed_at'] else None,
                retry_count=int(data['retry_count']),
                max_retries=int(data['max_retries']),
                error_message=data['error_message'] if data['error_message'] else None,
                processing_timeout=int(data['processing_timeout'])
            )
        except Exception as e:
            logger.error(f"Failed to parse message from Redis: {str(e)}")
            raise
    
    async def _move_to_completed(self, message: Message):
        """Move message to completed queue."""
        completed_key = self._get_completed_key(message.queue_name)
        score = datetime.utcnow().timestamp()
        self.redis_client.zadd(completed_key, {message.message_id: score})
        
        # Keep only recent completed messages
        self.redis_client.zremrangebyrank(completed_key, 0, -1000)
    
    async def _move_to_dlq(self, message: Message):
        """Move message to dead letter queue."""
        dlq_key = self._get_dlq_key(message.queue_name)
        score = datetime.utcnow().timestamp()
        self.redis_client.zadd(dlq_key, {message.message_id: score})
    
    def _calculate_priority_score(self, message: Message) -> float:
        """Calculate priority score for queue ordering."""
        # Higher priority = lower score (for ZPOPMIN)
        priority_score = (10 - message.priority) * 1000000
        
        # Add timestamp component for FIFO within same priority
        timestamp_score = message.created_at.timestamp()
        
        return priority_score + timestamp_score
    
    def _get_queue_key(self, queue_name: str) -> str:
        return f"queue:{queue_name}"
    
    def _get_processing_key(self, queue_name: str) -> str:
        return f"queue:processing:{queue_name}"
    
    def _get_completed_key(self, queue_name: str) -> str:
        return f"queue:completed:{queue_name}"
    
    def _get_dlq_key(self, queue_name: str) -> str:
        return f"queue:{settings.dead_letter_queue_prefix}:{queue_name}"
    
    def _get_message_key(self, message_id: str) -> str:
        return f"message:{message_id}"
    
    async def cleanup_old_messages(self):
        """Cleanup old completed and failed messages."""
        try:
            cutoff_time = datetime.utcnow() - timedelta(days=7)
            cutoff_timestamp = cutoff_time.timestamp()
            
            # Find all completed and DLQ keys
            completed_keys = self.redis_client.keys("queue:completed:*")
            dlq_keys = self.redis_client.keys(f"queue:{settings.dead_letter_queue_prefix}:*")
            
            total_cleaned = 0
            
            for key in completed_keys + dlq_keys:
                # Remove old entries
                removed = self.redis_client.zremrangebyscore(key, 0, cutoff_timestamp)
                total_cleaned += removed
            
            logger.info(f"Cleaned up {total_cleaned} old messages")
            return total_cleaned
            
        except Exception as e:
            logger.error(f"Failed to cleanup old messages: {str(e)}")
            return 0