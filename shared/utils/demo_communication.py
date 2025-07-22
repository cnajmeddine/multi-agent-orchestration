#  Demo all Communication Service features
import asyncio
import httpx
import json
import time
from datetime import datetime

COMM_SERVICE_URL = "http://localhost:8004"

async def test_communication_service():
    """Test all Communication Service features."""
    
    print("🚀 COMMUNICATION SERVICE DEMO")
    print("=" * 50)
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        
        # 1. Health Check
        print("\n1. 📊 HEALTH CHECK")
        await test_health_check(client)
        
        # 2. Event Publishing and Streams
        print("\n2. 📡 EVENT PUBLISHING & STREAMS")
        await test_events(client)
        
        # 3. Webhook Management
        print("\n3. 🔗 WEBHOOK MANAGEMENT")
        webhook_id = await test_webhooks(client)
        
        # 4. Message Queues
        print("\n4. 📬 MESSAGE QUEUES")
        await test_queues(client)
        
        # 5. Integration Test
        print("\n5. 🔄 INTEGRATION TEST")
        await test_integration(client, webhook_id)
        
        # 6. Service Stats
        print("\n6. 📈 SERVICE STATISTICS")
        await test_service_stats(client)

async def test_health_check(client):
    """Test health check endpoints."""
    try:
        # Basic health check
        response = await client.get(f"{COMM_SERVICE_URL}/health/")
        print(f"✅ Basic health: {response.json()['status']}")
        
        # Detailed health check
        response = await client.get(f"{COMM_SERVICE_URL}/health/detailed")
        health = response.json()
        print(f"✅ Detailed health: {health['status']}")
        
        # Show component status
        for component, status in health.get('components', {}).items():
            print(f"   - {component}: {status.get('status', 'unknown')}")
            
    except Exception as e:
        print(f"❌ Health check failed: {str(e)}")

async def test_events(client):
    """Test event publishing and streams."""
    try:
        # Publish a test event
        event_data = {
            "event_type": "system.alert",
            "source_service": "demo-script",
            "source_id": "test-001",
            "priority": "medium",
            "payload": {
                "message": "This is a test event from demo script",
                "timestamp": datetime.utcnow().isoformat(),
                "test": True
            },
            "metadata": {
                "demo": True,
                "version": "1.0"
            }
        }
        
        response = await client.post(f"{COMM_SERVICE_URL}/events/publish", json=event_data)
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Published event: {result['event_id']}")
        else:
            print(f"❌ Failed to publish event: {response.status_code}")
            return
        
        # Publish workflow events
        workflow_event = {
            "event_type": "workflow.started",
            "workflow_id": "demo-workflow-001",
            "execution_id": "exec-123",
            "payload": {
                "workflow_name": "Demo Workflow",
                "started_by": "demo-script"
            }
        }
        
        response = await client.post(f"{COMM_SERVICE_URL}/events/publish/workflow", params=workflow_event)
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Published workflow event: {result['event_id']}")
        
        # List streams
        response = await client.get(f"{COMM_SERVICE_URL}/events/streams")
        if response.status_code == 200:
            streams = response.json()
            print(f"✅ Found {len(streams)} event streams:")
            for stream in streams[:3]:  # Show first 3
                print(f"   - {stream['stream_name']}: {stream['length']} events")
        
        # Get event stats
        response = await client.get(f"{COMM_SERVICE_URL}/events/stats")
        if response.status_code == 200:
            stats = response.json()
            print(f"✅ Event stats: {stats.get('active_subscriptions', 0)} subscriptions")
            
    except Exception as e:
        print(f"❌ Event test failed: {str(e)}")

async def test_webhooks(client):
    """Test webhook management."""
    webhook_id = None
    
    try:
        # Create a webhook (using webhook.site for testing)
        webhook_data = {
            "name": "Demo Webhook",
            "url": "https://webhook.site/unique-id-here",  # Replace with real webhook.site URL
            "event_filter": {
                "event_types": ["system.alert", "workflow.started", "workflow.completed"],
                "source_services": ["demo-script", "workflow-service"],
                "priority_levels": ["medium", "high"]
            },
            "timeout": 30,
            "headers": {
                "X-Demo": "true",
                "Authorization": "Bearer demo-token"
            }
        }
        
        response = await client.post(f"{COMM_SERVICE_URL}/webhooks/", json=webhook_data)
        if response.status_code == 200:
            webhook = response.json()
            webhook_id = webhook['webhook_id']
            print(f"✅ Created webhook: {webhook['name']} ({webhook_id[:8]}...)")
        else:
            print(f"❌ Failed to create webhook: {response.status_code}")
            print(f"   Response: {response.text}")
            return None
        
        # List webhooks
        response = await client.get(f"{COMM_SERVICE_URL}/webhooks/")
        if response.status_code == 200:
            webhooks = response.json()
            print(f"✅ Listed {len(webhooks)} webhooks")
        
        # Test webhook (this will send a test event)
        response = await client.post(f"{COMM_SERVICE_URL}/webhooks/{webhook_id}/test")
        if response.status_code == 200:
            delivery = response.json()
            print(f"✅ Webhook test sent: {delivery['status']}")
        
        # Get webhook stats
        response = await client.get(f"{COMM_SERVICE_URL}/webhooks/stats/overview")
        if response.status_code == 200:
            stats = response.json()
            print(f"✅ Webhook stats: {stats.get('total_webhooks', 0)} total, {stats.get('active_webhooks', 0)} active")
            
        return webhook_id
        
    except Exception as e:
        print(f"❌ Webhook test failed: {str(e)}")
        return None

async def test_queues(client):
    """Test message queue functionality."""
    try:
        queue_name = "demo-queue"
        
        # Register a test handler for the queue
        response = await client.post(
            f"{COMM_SERVICE_URL}/queues/{queue_name}/register-handler",
            params={"handler_name": "demo-handler", "max_concurrent": 2}
        )
        if response.status_code == 200:
            print(f"✅ Registered handler for queue: {queue_name}")
        
        # Enqueue some test messages
        for i in range(5):
            message_data = {
                "queue_name": queue_name,
                "payload": {
                    "task": f"demo-task-{i+1}",
                    "data": f"Sample data for task {i+1}",
                    "timestamp": datetime.utcnow().isoformat()
                },
                "priority": 5 + (i % 3),  # Vary priority
                "delay_seconds": 0 if i < 3 else 2,  # Some delayed messages
                "max_retries": 3
            }
            
            response = await client.post(f"{COMM_SERVICE_URL}/queues/enqueue", json=message_data)
            if response.status_code == 200:
                result = response.json()
                print(f"✅ Enqueued message {i+1}: {result['message_id'][:8]}...")
        
        # Wait a moment for processing
        print("⏳ Waiting for message processing...")
        await asyncio.sleep(3)
        
        # Check queue stats
        response = await client.get(f"{COMM_SERVICE_URL}/queues/{queue_name}/stats")
        if response.status_code == 200:
            stats = response.json()
            print(f"✅ Queue stats for '{queue_name}':")
            print(f"   - Pending: {stats['pending_messages']}")
            print(f"   - Processing: {stats['processing_messages']}")
            print(f"   - Completed: {stats['completed_messages']}")
            print(f"   - Failed: {stats['failed_messages']}")
            print(f"   - Avg processing time: {stats['average_processing_time']:.2f}s")
        
        # Send some test messages
        response = await client.post(
            f"{COMM_SERVICE_URL}/queues/test/{queue_name}",
            params={"message_count": 3}
        )
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Sent {result['message_count']} test messages")
            
    except Exception as e:
        print(f"❌ Queue test failed: {str(e)}")

async def test_integration(client, webhook_id):
    """Test integration between events, queues, and webhooks."""
    try:
        print("Testing end-to-end event flow...")
        
        # Publish events that should trigger webhooks
        test_events = [
            {
                "event_type": "workflow.started",
                "workflow_id": "integration-test-workflow",
                "execution_id": "exec-integration-001",
                "payload": {
                    "workflow_name": "Integration Test Workflow",
                    "test_type": "integration"
                }
            },
            {
                "event_type": "workflow.completed", 
                "workflow_id": "integration-test-workflow",
                "execution_id": "exec-integration-001",
                "payload": {
                    "status": "success",
                    "duration": "45.2s",
                    "steps_completed": 3
                }
            }
        ]
        
        for i, event in enumerate(test_events):
            response = await client.post(f"{COMM_SERVICE_URL}/events/publish/workflow", params=event)
            if response.status_code == 200:
                result = response.json()
                print(f"✅ Integration event {i+1}: {result['event_id'][:8]}...")
            
            # Small delay between events
            await asyncio.sleep(0.5)
        
        # Enqueue related messages
        queue_message = {
            "queue_name": "integration-queue",
            "payload": {
                "workflow_id": "integration-test-workflow",
                "action": "cleanup",
                "integration_test": True
            },
            "priority": 8
        }
        
        response = await client.post(f"{COMM_SERVICE_URL}/queues/enqueue", json=queue_message)
        if response.status_code == 200:
            print(f"✅ Enqueued integration message")
        
        print("✅ Integration test completed - check webhook.site for deliveries!")
        
    except Exception as e:
        print(f"❌ Integration test failed: {str(e)}")

async def test_service_stats(client):
    """Get overall service statistics."""
    try:
        response = await client.get(f"{COMM_SERVICE_URL}/stats")
        if response.status_code == 200:
            stats = response.json()
            print(f"✅ Service Statistics:")
            print(f"   - Service: {stats['service']}")
            
            # Event stats
            events = stats.get('components', {}).get('events', {})
            if events:
                print(f"   - Active subscriptions: {events.get('active_subscriptions', 0)}")
                print(f"   - Event streams: {len(events.get('stream_info', {}))}")
            
            # Webhook stats
            webhooks = stats.get('components', {}).get('webhooks', {})
            if webhooks:
                print(f"   - Total webhooks: {webhooks.get('total_webhooks', 0)}")
                print(f"   - Webhook success rate: {webhooks.get('success_rate', 0):.1f}%")
            
            # Queue stats
            queues = stats.get('components', {}).get('queues', {})
            if queues:
                print(f"   - Total queues: {queues.get('total_queues', 0)}")
                
        # Root endpoint
        response = await client.get(f"{COMM_SERVICE_URL}/")
        if response.status_code == 200:
            info = response.json()
            print(f"✅ Service Info:")
            print(f"   - Status: {info['status']}")
            print(f"   - Features: {', '.join(info['features'])}")
            
    except Exception as e:
        print(f"❌ Stats test failed: {str(e)}")

async def cleanup_demo_data(client):
    """Clean up demo data (optional)."""
    try:
        print("\n🧹 CLEANUP (Optional)")
        
        # List and optionally delete webhooks
        response = await client.get(f"{COMM_SERVICE_URL}/webhooks/")
        if response.status_code == 200:
            webhooks = response.json()
            for webhook in webhooks:
                if "Demo" in webhook.get('name', ''):
                    # Optionally delete demo webhooks
                    # await client.delete(f"{COMM_SERVICE_URL}/webhooks/{webhook['webhook_id']}")
                    print(f"📝 Demo webhook found: {webhook['name']}")
        
        print("✅ Cleanup completed")
        
    except Exception as e:
        print(f"❌ Cleanup failed: {str(e)}")

if __name__ == "__main__":
    print("Starting Communication Service Demo...")
    print("Make sure the communication service is running on port 8004!")
    print()
    
    # Run the demo
    try:
        asyncio.run(test_communication_service())
        print("\n🎉 DEMO COMPLETED SUCCESSFULLY!")
        print("\nNext steps:")
        print("1. Check the service logs for detailed information")
        print("2. Visit http://localhost:8004/docs for API documentation")
        print("3. Use webhook.site to test webhook deliveries")
        print("4. Monitor Redis streams with Redis CLI")
        
    except KeyboardInterrupt:
        print("\n❌ Demo interrupted by user")
    except Exception as e:
        print(f"\n❌ Demo failed: {str(e)}")
        print("\nTroubleshooting:")
        print("1. Make sure Redis is running (docker-compose up redis -d)")
        print("2. Start the communication service (python run_communication_service.py)")
        print("3. Check the service health at http://localhost:8004/health/")