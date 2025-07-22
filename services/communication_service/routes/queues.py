# API endpoints for queue management and message operations. 
# services/communication_service/routes/queues.py
"""API routes for message queue management."""

from fastapi import APIRouter, HTTPException, Depends, Request
from typing import List, Optional, Dict, Any
from datetime import datetime
import logging

from ..models import (
    Message, MessageEnqueueRequest, QueueStats, MessageStatus
)
from ..queue_manager import QueueManager

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/queues", tags=["queues"])

def get_queue_manager(request: Request) -> QueueManager:
    """Get queue manager from app state."""
    if not hasattr(request.app.state, 'queue_manager'):
        raise HTTPException(status_code=500, detail="Queue manager not initialized")
    return request.app.state.queue_manager

@router.post("/enqueue")
async def enqueue_message(
    request: MessageEnqueueRequest,
    queue_manager: QueueManager = Depends(get_queue_manager)
):
    """Enqueue a message for processing."""
    try:
        message_id = await queue_manager.enqueue_message(request)
        
        return {
            "message_id": message_id,
            "queue_name": request.queue_name,
            "status": "enqueued"
        }
        
    except Exception as e:
        logger.error(f"Failed to enqueue message: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/", response_model=List[QueueStats])
async def list_queues(
    queue_manager: QueueManager = Depends(get_queue_manager)
):
    """List all queues with statistics."""
    try:
        stats = await queue_manager.get_all_queue_stats()
        return stats
        
    except Exception as e:
        logger.error(f"Failed to list queues: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{queue_name}/stats", response_model=QueueStats)
async def get_queue_stats(
    queue_name: str,
    queue_manager: QueueManager = Depends(get_queue_manager)
):
    """Get statistics for a specific queue."""
    try:
        stats = await queue_manager.get_queue_stats(queue_name)
        return stats
        
    except Exception as e:
        logger.error(f"Failed to get queue stats for {queue_name}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/messages/{message_id}", response_model=Message)
async def get_message(
    message_id: str,
    queue_manager: QueueManager = Depends(get_queue_manager)
):
    """Get a specific message."""
    try:
        message = await queue_manager.get_message(message_id)
        
        if not message:
            raise HTTPException(status_code=404, detail="Message not found")
        
        return message
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get message {message_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{queue_name}/register-handler")
async def register_queue_handler(
    queue_name: str,
    handler_name: str,
    max_concurrent: int = 1,
    queue_manager: QueueManager = Depends(get_queue_manager)
):
    """Register a handler for a queue (for testing purposes)."""
    try:
        # Simple test handler
        async def test_handler(message: Message):
            logger.info(f"Processing message {message.message_id} from queue {queue_name}")
            # Simulate some work
            import asyncio
            await asyncio.sleep(0.1)
            logger.info(f"Completed message {message.message_id}")
        
        await queue_manager.register_queue_handler(
            queue_name=queue_name,
            handler=test_handler,
            max_concurrent=max_concurrent
        )
        
        return {
            "queue_name": queue_name,
            "handler_name": handler_name,
            "max_concurrent": max_concurrent,
            "status": "registered"
        }
        
    except Exception as e:
        logger.error(f"Failed to register handler for queue {queue_name}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/{queue_name}/handler")
async def unregister_queue_handler(
    queue_name: str,
    queue_manager: QueueManager = Depends(get_queue_manager)
):
    """Unregister a queue handler."""
    try:
        await queue_manager.unregister_queue_handler(queue_name)
        
        return {
            "queue_name": queue_name,
            "status": "unregistered"
        }
        
    except Exception as e:
        logger.error(f"Failed to unregister handler for queue {queue_name}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{queue_name}/requeue-dlq")
async def requeue_dead_letter_messages(
    queue_name: str,
    limit: int = 10,
    queue_manager: QueueManager = Depends(get_queue_manager)
):
    """Requeue messages from dead letter queue."""
    try:
        requeued_count = await queue_manager.requeue_dead_letter_messages(
            queue_name=queue_name,
            limit=limit
        )
        
        return {
            "queue_name": queue_name,
            "requeued_count": requeued_count,
            "status": "completed"
        }
        
    except Exception as e:
        logger.error(f"Failed to requeue DLQ messages for {queue_name}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/{queue_name}/purge")
async def purge_queue(
    queue_name: str,
    confirm: bool = False,
    queue_manager: QueueManager = Depends(get_queue_manager)
):
    """Purge all messages from a queue."""
    try:
        if not confirm:
            raise HTTPException(
                status_code=400, 
                detail="Must set confirm=true to purge queue"
            )
        
        purged_count = await queue_manager.purge_queue(queue_name)
        
        return {
            "queue_name": queue_name,
            "purged_count": purged_count,
            "status": "purged"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to purge queue {queue_name}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/test/{queue_name}")
async def send_test_message(
    queue_name: str,
    message_count: int = 1,
    queue_manager: QueueManager = Depends(get_queue_manager)
):
    """Send test messages to a queue."""
    try:
        message_ids = []
        
        for i in range(message_count):
            request = MessageEnqueueRequest(
                queue_name=queue_name,
                payload={
                    "test": True,
                    "message_number": i + 1,
                    "total_messages": message_count,
                    "timestamp": str(datetime.utcnow())
                },
                priority=5
            )
            
            message_id = await queue_manager.enqueue_message(request)
            message_ids.append(message_id)
        
        return {
            "queue_name": queue_name,
            "message_count": message_count,
            "message_ids": message_ids,
            "status": "test messages sent"
        }
        
    except Exception as e:
        logger.error(f"Failed to send test messages to {queue_name}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))