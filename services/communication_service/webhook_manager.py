# Manages registration, delivery, and processing of webhooks for external integrations. 
# services/communication_service/webhook_manager.py
"""Webhook manager for external notifications and integrations."""

import asyncio
import httpx
import json
import hmac
import hashlib
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import uuid

from .models import (
    Webhook, WebhookDelivery, WebhookStatus, Event, EventType, 
    WebhookCreateRequest, WebhookUpdateRequest
)
from .config import settings

logger = logging.getLogger(__name__)

class WebhookManager:
    """Manages webhook registrations and deliveries."""
    
    def __init__(self):
        self.webhooks: Dict[str, Webhook] = {}
        self.delivery_queue: asyncio.Queue = asyncio.Queue()
        self.delivery_workers: List[asyncio.Task] = []
        self.running = False
        self.http_client: Optional[httpx.AsyncClient] = None
        
    async def start(self):
        """Start the webhook manager."""
        try:
            self.running = True
            
            # Initialize HTTP client with reasonable defaults
            self.http_client = httpx.AsyncClient(
                timeout=httpx.Timeout(30.0),
                limits=httpx.Limits(
                    max_connections=settings.max_concurrent_webhooks,
                    max_keepalive_connections=20
                )
            )
            
            # Start delivery workers
            for i in range(min(10, settings.max_concurrent_webhooks)):
                worker = asyncio.create_task(self._delivery_worker(f"worker-{i}"))
                self.delivery_workers.append(worker)
            
            logger.info(f"Webhook manager started with {len(self.delivery_workers)} workers")
            
        except Exception as e:
            logger.error(f"Failed to start webhook manager: {str(e)}")
            raise
    
    async def stop(self):
        """Stop the webhook manager."""
        self.running = False
        
        # Cancel delivery workers
        for worker in self.delivery_workers:
            worker.cancel()
        
        # Wait for workers to finish
        if self.delivery_workers:
            await asyncio.gather(*self.delivery_workers, return_exceptions=True)
        
        # Close HTTP client
        if self.http_client:
            await self.http_client.aclose()
        
        logger.info("Webhook manager stopped")
    
    async def create_webhook(self, request: WebhookCreateRequest) -> Webhook:
        """Create a new webhook."""
        try:
            webhook = Webhook(
                name=request.name,
                url=request.url,
                event_filter=request.event_filter,
                secret_token=request.secret_token,
                headers=request.headers,
                timeout=request.timeout
            )
            
            self.webhooks[webhook.webhook_id] = webhook
            
            logger.info(f"Created webhook {webhook.webhook_id}: {webhook.name}")
            return webhook
            
        except Exception as e:
            logger.error(f"Failed to create webhook: {str(e)}")
            raise
    
    async def update_webhook(self, webhook_id: str, request: WebhookUpdateRequest) -> Webhook:
        """Update an existing webhook."""
        try:
            if webhook_id not in self.webhooks:
                raise ValueError(f"Webhook {webhook_id} not found")
            
            webhook = self.webhooks[webhook_id]
            
            # Update fields if provided
            if request.name is not None:
                webhook.name = request.name
            if request.url is not None:
                webhook.url = request.url
            if request.event_filter is not None:
                webhook.event_filter = request.event_filter
            if request.secret_token is not None:
                webhook.secret_token = request.secret_token
            if request.headers is not None:
                webhook.headers = request.headers
            if request.timeout is not None:
                webhook.timeout = request.timeout
            if request.status is not None:
                webhook.status = request.status
            
            logger.info(f"Updated webhook {webhook_id}")
            return webhook
            
        except Exception as e:
            logger.error(f"Failed to update webhook {webhook_id}: {str(e)}")
            raise
    
    async def delete_webhook(self, webhook_id: str) -> bool:
        """Delete a webhook."""
        try:
            if webhook_id in self.webhooks:
                del self.webhooks[webhook_id]
                logger.info(f"Deleted webhook {webhook_id}")
                return True
            else:
                logger.warning(f"Webhook {webhook_id} not found for deletion")
                return False
                
        except Exception as e:
            logger.error(f"Failed to delete webhook {webhook_id}: {str(e)}")
            return False
    
    async def get_webhook(self, webhook_id: str) -> Optional[Webhook]:
        """Get a webhook by ID."""
        return self.webhooks.get(webhook_id)
    
    async def list_webhooks(self) -> List[Webhook]:
        """List all webhooks."""
        return list(self.webhooks.values())
    
    async def trigger_webhook(self, event: Event) -> List[WebhookDelivery]:
        """Trigger webhooks that match the event."""
        try:
            deliveries = []
            
            for webhook in self.webhooks.values():
                if await self._should_trigger_webhook(webhook, event):
                    delivery = WebhookDelivery(
                        webhook_id=webhook.webhook_id,
                        event_id=event.event_id
                    )
                    
                    # Queue for delivery
                    await self.delivery_queue.put((webhook, event, delivery))
                    deliveries.append(delivery)
                    
                    logger.debug(f"Queued webhook {webhook.webhook_id} for event {event.event_id}")
            
            return deliveries
            
        except Exception as e:
            logger.error(f"Failed to trigger webhooks for event {event.event_id}: {str(e)}")
            return []
    
    async def _should_trigger_webhook(self, webhook: Webhook, event: Event) -> bool:
        """Check if a webhook should be triggered for an event."""
        if webhook.status != WebhookStatus.ACTIVE:
            return False
        
        filter_config = webhook.event_filter
        
        # Check event types
        if filter_config.event_types and event.event_type not in filter_config.event_types:
            return False
        
        # Check source services
        if filter_config.source_services and event.source_service not in filter_config.source_services:
            return False
        
        # Check priority levels
        if filter_config.priority_levels and event.priority not in filter_config.priority_levels:
            return False
        
        return True
    
    async def _delivery_worker(self, worker_name: str):
        """Worker that processes webhook deliveries."""
        logger.info(f"Webhook delivery worker {worker_name} started")
        
        while self.running:
            try:
                # Get delivery from queue with timeout
                try:
                    webhook, event, delivery = await asyncio.wait_for(
                        self.delivery_queue.get(), timeout=1.0
                    )
                except asyncio.TimeoutError:
                    continue
                
                # Process the delivery
                await self._process_delivery(webhook, event, delivery)
                
            except Exception as e:
                logger.error(f"Webhook worker {worker_name} error: {str(e)}")
                await asyncio.sleep(1)
        
        logger.info(f"Webhook delivery worker {worker_name} stopped")
    
    async def _process_delivery(self, webhook: Webhook, event: Event, delivery: WebhookDelivery):
        """Process a single webhook delivery with retries."""
        max_attempts = webhook.retry_config.get("max_attempts", 3)
        backoff_multiplier = webhook.retry_config.get("backoff_multiplier", 2.0)
        initial_delay = webhook.retry_config.get("initial_delay", 1)
        
        for attempt in range(1, max_attempts + 1):
            delivery.attempt = attempt
            
            try:
                # Prepare payload
                payload = self._prepare_webhook_payload(webhook, event)
                
                # Prepare headers
                headers = dict(webhook.headers)
                headers["Content-Type"] = "application/json"
                headers["User-Agent"] = f"AI-Orchestration-Platform/1.0"
                headers["X-Event-ID"] = event.event_id
                headers["X-Event-Type"] = event.event_type.value
                headers["X-Delivery-ID"] = delivery.delivery_id
                
                # Add signature if secret token provided
                if webhook.secret_token:
                    signature = self._generate_signature(payload, webhook.secret_token)
                    headers[settings.webhook_signature_header] = signature
                
                # Make HTTP request
                start_time = datetime.utcnow()
                response = await self.http_client.post(
                    str(webhook.url),
                    json=payload,
                    headers=headers,
                    timeout=webhook.timeout
                )
                
                end_time = datetime.utcnow()
                duration_ms = int((end_time - start_time).total_seconds() * 1000)
                
                # Update delivery record
                delivery.status = "success"
                delivery.response_status = response.status_code
                delivery.response_body = response.text[:1000]  # Limit response body size
                delivery.delivered_at = end_time
                delivery.duration_ms = duration_ms
                
                # Update webhook stats
                webhook.success_count += 1
                webhook.last_triggered_at = end_time
                
                logger.info(
                    f"Webhook {webhook.webhook_id} delivered successfully "
                    f"(attempt {attempt}, {duration_ms}ms, status {response.status_code})"
                )
                
                return  # Success, exit retry loop
                
            except httpx.TimeoutException:
                error_msg = f"Webhook timeout after {webhook.timeout}s"
                logger.warning(f"Webhook {webhook.webhook_id} delivery timeout (attempt {attempt})")
                
            except httpx.HTTPStatusError as e:
                error_msg = f"HTTP {e.response.status_code}: {e.response.text[:200]}"
                logger.warning(
                    f"Webhook {webhook.webhook_id} HTTP error {e.response.status_code} (attempt {attempt})"
                )
                
            except Exception as e:
                error_msg = f"Delivery error: {str(e)}"
                logger.error(f"Webhook {webhook.webhook_id} delivery error (attempt {attempt}): {str(e)}")
            
            # Update delivery record with error
            delivery.status = "failed"
            delivery.error_message = error_msg
            
            # Wait before retry (except on last attempt)
            if attempt < max_attempts:
                delay = initial_delay * (backoff_multiplier ** (attempt - 1))
                await asyncio.sleep(delay)
        
        # All attempts failed
        webhook.failure_count += 1
        
        # Disable webhook if too many failures
        if webhook.failure_count > 10:
            webhook.status = WebhookStatus.FAILED
            logger.warning(f"Disabled webhook {webhook.webhook_id} due to repeated failures")
        
        logger.error(f"Webhook {webhook.webhook_id} delivery failed after {max_attempts} attempts")
    
    def _prepare_webhook_payload(self, webhook: Webhook, event: Event) -> Dict[str, Any]:
        """Prepare the payload for webhook delivery."""
        return {
            "event_id": event.event_id,
            "event_type": event.event_type.value,
            "source_service": event.source_service,
            "source_id": event.source_id,
            "priority": event.priority.value,
            "timestamp": event.timestamp.isoformat(),
            "correlation_id": event.correlation_id,
            "payload": event.payload,
            "metadata": event.metadata,
            "webhook": {
                "webhook_id": webhook.webhook_id,
                "name": webhook.name
            }
        }
    
    def _generate_signature(self, payload: Dict[str, Any], secret: str) -> str:
        """Generate HMAC signature for webhook payload."""
        payload_bytes = json.dumps(payload, sort_keys=True).encode('utf-8')
        signature = hmac.new(
            secret.encode('utf-8'),
            payload_bytes,
            hashlib.sha256
        ).hexdigest()
        return f"sha256={signature}"
    
    async def get_webhook_stats(self) -> Dict[str, Any]:
        """Get webhook statistics."""
        try:
            total_webhooks = len(self.webhooks)
            active_webhooks = sum(1 for w in self.webhooks.values() if w.status == WebhookStatus.ACTIVE)
            total_deliveries = sum(w.success_count + w.failure_count for w in self.webhooks.values())
            successful_deliveries = sum(w.success_count for w in self.webhooks.values())
            
            return {
                "total_webhooks": total_webhooks,
                "active_webhooks": active_webhooks,
                "inactive_webhooks": total_webhooks - active_webhooks,
                "total_deliveries": total_deliveries,
                "successful_deliveries": successful_deliveries,
                "failed_deliveries": total_deliveries - successful_deliveries,
                "success_rate": (successful_deliveries / total_deliveries * 100) if total_deliveries > 0 else 0,
                "queue_size": self.delivery_queue.qsize(),
                "active_workers": len([w for w in self.delivery_workers if not w.done()])
            }
            
        except Exception as e:
            logger.error(f"Failed to get webhook stats: {str(e)}")
            return {}
    
    async def test_webhook(self, webhook_id: str) -> WebhookDelivery:
        """Send a test event to a webhook."""
        try:
            webhook = self.webhooks.get(webhook_id)
            if not webhook:
                raise ValueError(f"Webhook {webhook_id} not found")
            
            # Create test event
            test_event = Event(
                event_type=EventType.SYSTEM_ALERT,
                source_service="communication-service",
                source_id="test",
                payload={"message": "This is a test webhook delivery"}
            )
            
            delivery = WebhookDelivery(
                webhook_id=webhook.webhook_id,
                event_id=test_event.event_id
            )
            
            # Process delivery immediately
            await self._process_delivery(webhook, test_event, delivery)
            
            return delivery
            
        except Exception as e:
            logger.error(f"Failed to test webhook {webhook_id}: {str(e)}")
            raise