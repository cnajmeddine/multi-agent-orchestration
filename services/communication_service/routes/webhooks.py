# API endpoints for webhook registration, delivery, and management. 
# services/communication_service/routes/webhooks.py
"""API routes for webhook management."""

from fastapi import APIRouter, HTTPException, Depends, Request
from typing import List, Optional, Dict, Any
import logging

from ..models import (
    Webhook, WebhookCreateRequest, WebhookUpdateRequest, 
    WebhookDelivery, WebhookStatus
)
from ..webhook_manager import WebhookManager

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/webhooks", tags=["webhooks"])

def get_webhook_manager(request: Request) -> WebhookManager:
    """Get webhook manager from app state."""
    if not hasattr(request.app.state, 'webhook_manager'):
        raise HTTPException(status_code=500, detail="Webhook manager not initialized")
    return request.app.state.webhook_manager

@router.post("/", response_model=Webhook)
async def create_webhook(
    request: WebhookCreateRequest,
    webhook_manager: WebhookManager = Depends(get_webhook_manager)
):
    """Create a new webhook."""
    try:
        webhook = await webhook_manager.create_webhook(request)
        
        logger.info(f"Created webhook {webhook.webhook_id}: {webhook.name}")
        return webhook
        
    except Exception as e:
        logger.error(f"Failed to create webhook: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/", response_model=List[Webhook])
async def list_webhooks(
    webhook_manager: WebhookManager = Depends(get_webhook_manager)
):
    """List all webhooks."""
    try:
        webhooks = await webhook_manager.list_webhooks()
        return webhooks
        
    except Exception as e:
        logger.error(f"Failed to list webhooks: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{webhook_id}", response_model=Webhook)
async def get_webhook(
    webhook_id: str,
    webhook_manager: WebhookManager = Depends(get_webhook_manager)
):
    """Get a specific webhook."""
    try:
        webhook = await webhook_manager.get_webhook(webhook_id)
        
        if not webhook:
            raise HTTPException(status_code=404, detail="Webhook not found")
        
        return webhook
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get webhook {webhook_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/{webhook_id}", response_model=Webhook)
async def update_webhook(
    webhook_id: str,
    request: WebhookUpdateRequest,
    webhook_manager: WebhookManager = Depends(get_webhook_manager)
):
    """Update a webhook."""
    try:
        webhook = await webhook_manager.update_webhook(webhook_id, request)
        
        logger.info(f"Updated webhook {webhook_id}")
        return webhook
        
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to update webhook {webhook_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/{webhook_id}")
async def delete_webhook(
    webhook_id: str,
    webhook_manager: WebhookManager = Depends(get_webhook_manager)
):
    """Delete a webhook."""
    try:
        success = await webhook_manager.delete_webhook(webhook_id)
        
        if not success:
            raise HTTPException(status_code=404, detail="Webhook not found")
        
        return {"webhook_id": webhook_id, "status": "deleted"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete webhook {webhook_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{webhook_id}/test", response_model=WebhookDelivery)
async def test_webhook(
    webhook_id: str,
    webhook_manager: WebhookManager = Depends(get_webhook_manager)
):
    """Send a test event to a webhook."""
    try:
        delivery = await webhook_manager.test_webhook(webhook_id)
        
        logger.info(f"Sent test event to webhook {webhook_id}")
        return delivery
        
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to test webhook {webhook_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{webhook_id}/enable")
async def enable_webhook(
    webhook_id: str,
    webhook_manager: WebhookManager = Depends(get_webhook_manager)
):
    """Enable a webhook."""
    try:
        update_request = WebhookUpdateRequest(status=WebhookStatus.ACTIVE)
        webhook = await webhook_manager.update_webhook(webhook_id, update_request)
        
        return {
            "webhook_id": webhook_id,
            "status": "enabled",
            "webhook_status": webhook.status
        }
        
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to enable webhook {webhook_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{webhook_id}/disable")
async def disable_webhook(
    webhook_id: str,
    webhook_manager: WebhookManager = Depends(get_webhook_manager)
):
    """Disable a webhook."""
    try:
        update_request = WebhookUpdateRequest(status=WebhookStatus.INACTIVE)
        webhook = await webhook_manager.update_webhook(webhook_id, update_request)
        
        return {
            "webhook_id": webhook_id,
            "status": "disabled",
            "webhook_status": webhook.status
        }
        
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to disable webhook {webhook_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/stats/overview")
async def get_webhook_stats(
    webhook_manager: WebhookManager = Depends(get_webhook_manager)
):
    """Get webhook statistics."""
    try:
        stats = await webhook_manager.get_webhook_stats()
        return stats
        
    except Exception as e:
        logger.error(f"Failed to get webhook stats: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{webhook_id}/stats")
async def get_webhook_details(
    webhook_id: str,
    webhook_manager: WebhookManager = Depends(get_webhook_manager)
):
    """Get detailed statistics for a specific webhook."""
    try:
        webhook = await webhook_manager.get_webhook(webhook_id)
        
        if not webhook:
            raise HTTPException(status_code=404, detail="Webhook not found")
        
        return {
            "webhook_id": webhook_id,
            "name": webhook.name,
            "status": webhook.status,
            "url": str(webhook.url),
            "success_count": webhook.success_count,
            "failure_count": webhook.failure_count,
            "total_deliveries": webhook.success_count + webhook.failure_count,
            "success_rate": (
                webhook.success_count / (webhook.success_count + webhook.failure_count) * 100
                if (webhook.success_count + webhook.failure_count) > 0 else 0
            ),
            "last_triggered_at": webhook.last_triggered_at,
            "created_at": webhook.created_at,
            "event_filter": webhook.event_filter.dict(),
            "timeout": webhook.timeout
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get webhook details {webhook_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))