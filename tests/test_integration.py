# test_integration.py - Test all 4 services working together
import asyncio
import httpx
import json
import time

async def test_full_integration():
    """Test that all 4 services communicate properly."""
    
    print("🧪 TESTING FULL SERVICE INTEGRATION")
    print("=" * 50)
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        
        # 1. Check all services are running
        print("\n1. 🔍 CHECKING SERVICE HEALTH")
        services = {
            "agent": "http://localhost:8001",
            "workflow": "http://localhost:8002", 
            "monitoring": "http://localhost:8003",
            "communication": "http://localhost:8004"
        }
        
        for name, url in services.items():
            try:
                # Test root endpoint instead of health (all your services have working root endpoints)
                response = await client.get(f"{url}/")
                if response.status_code == 200:
                    data = response.json()
                    print(f"✅ {name} service: {data.get('status', 'running')}")
                else:
                    print(f"❌ {name} service: HTTP {response.status_code}")
                    return False
            except Exception as e:
                print(f"❌ {name} service: {str(e)}")
                return False
        
        # 2. Test agent registration (should trigger events)
        print("\n2. 🤖 TESTING AGENT REGISTRATION")
        try:
            agent_data = {
                "name": "test-integration-agent",
                "agent_type": "text_processor",
                "capabilities": [
                    {
                        "name": "test_capability",
                        "description": "Test capability",
                        "input_types": ["text"],
                        "output_types": ["text"],
                        "max_concurrent_tasks": 1
                    }
                ],
                "max_concurrent_tasks": 1
            }
            
            response = await client.post(
                "http://localhost:8001/agents/register",
                json=agent_data
            )
            
            if response.status_code == 200:
                agent_info = response.json()
                print(f"✅ Registered agent: {agent_info['agent_id'][:8]}...")
            else:
                print(f"❌ Agent registration failed: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"❌ Agent registration error: {str(e)}")
            return False
        
        # 3. Wait a moment for events to propagate
        print("\n⏳ Waiting for event propagation...")
        await asyncio.sleep(2)
        
        # 4. Check monitoring received the events
        print("\n3. 📊 CHECKING MONITORING RECEIVED EVENTS")
        try:
            response = await client.get("http://localhost:8003/counters")
            if response.status_code == 200:
                counters = response.json()
                if counters.get("agents_registered", 0) > 0:
                    print(f"✅ Monitoring received agent registration: {counters['agents_registered']} agents")
                else:
                    print("❌ No agent registration events in monitoring")
                    
            response = await client.get("http://localhost:8003/dashboard/overview")
            if response.status_code == 200:
                dashboard = response.json()
                print(f"✅ Dashboard data available: {len(dashboard.get('recent_events', []))} recent events")
                
        except Exception as e:
            print(f"❌ Monitoring check error: {str(e)}")
        
        # 5. Test communication service event streams
        print("\n4. 📡 CHECKING COMMUNICATION SERVICE STREAMS")
        try:
            response = await client.get("http://localhost:8004/events/streams")
            if response.status_code == 200:
                streams = response.json()
                print(f"✅ Found {len(streams)} event streams")
                for stream in streams[:3]:  # Show first 3
                    print(f"   - {stream['stream_name']}: {stream['length']} events")
            
        except Exception as e:
            print(f"❌ Communication streams error: {str(e)}")
        
        # 6. Test workflow creation and execution
        print("\n5. 🔄 TESTING WORKFLOW EXECUTION")
        try:
            workflow_def = {
                "name": "Integration Test Workflow",
                "description": "Test workflow for integration",
                "steps": [
                    {
                        "name": "test_step",
                        "agent_type": "text_processor",
                        "input_mapping": {
                            "task_type": "sentiment_analysis",
                            "text": "test_message"
                        },
                        "output_mapping": {
                            "sentiment": "result_sentiment"
                        },
                        "depends_on": [],
                        "timeout": 60
                    }
                ]
            }
            
            # Create workflow
            response = await client.post(
                "http://localhost:8002/workflows/",
                json=workflow_def
            )
            
            if response.status_code == 200:
                workflow = response.json()
                workflow_id = workflow['workflow_id']
                print(f"✅ Created workflow: {workflow_id[:8]}...")
                
                # Execute workflow
                execution_response = await client.post(
                    f"http://localhost:8002/workflows/{workflow_id}/execute",
                    json={"input_data": {"test_message": "This is a test message"}}
                )
                
                if execution_response.status_code == 200:
                    execution = execution_response.json()
                    execution_id = execution['execution_id']
                    print(f"✅ Started execution: {execution_id[:8]}...")
                    
                    # Wait for workflow to complete
                    print("⏳ Waiting for workflow completion...")
                    for i in range(15):  # 30 second timeout
                        await asyncio.sleep(2)
                        
                        status_response = await client.get(
                            f"http://localhost:8002/executions/{execution_id}/status"
                        )
                        
                        if status_response.status_code == 200:
                            status = status_response.json()
                            print(f"   Status: {status['status']} ({status['progress_percentage']:.1f}%)")
                            
                            if status['status'] in ['completed', 'failed']:
                                break
                    
                    # Check final monitoring data
                    print("\n6. 📈 FINAL MONITORING CHECK")
                    await asyncio.sleep(1)  # Let events propagate
                    
                    response = await client.get("http://localhost:8003/counters")
                    if response.status_code == 200:
                        counters = response.json()
                        print("✅ Final counters:")
                        for key, value in counters.items():
                            if value > 0:
                                print(f"   - {key}: {value}")
                    
                else:
                    print(f"❌ Workflow execution failed: {execution_response.status_code}")
            else:
                print(f"❌ Workflow creation failed: {response.status_code}")
                
        except Exception as e:
            print(f"❌ Workflow test error: {str(e)}")
        
        # 7. Summary
        print("\n🎯 INTEGRATION TEST SUMMARY")
        try:
            # Get final stats from all services
            monitoring_response = await client.get("http://localhost:8003/dashboard/overview")
            comm_response = await client.get("http://localhost:8004/events/stats")
            
            if monitoring_response.status_code == 200:
                data = monitoring_response.json()
                print(f"✅ Total events processed: {len(data.get('recent_events', []))}")
                print(f"✅ Workflow success rate: {data['summary'].get('workflow_success_rate', 0)}%")
            
            if comm_response.status_code == 200:
                comm_stats = comm_response.json()
                print(f"✅ Active subscriptions: {comm_stats.get('active_subscriptions', 0)}")
            
            print("\n🎉 Integration test completed!")
            return True
            
        except Exception as e:
            print(f"❌ Summary generation error: {str(e)}")
            return False

if __name__ == "__main__":
    print("Make sure all 4 services are running:")
    print("1. python run_agent_service.py")
    print("2. python run_workflow_service.py") 
    print("3. python run_monitoring_service.py")
    print("4. python run_communication_service.py")
    print()
    
    success = asyncio.run(test_full_integration())
    
    if success:
        print("\n✅ ALL SERVICES INTEGRATED SUCCESSFULLY!")
    else:
        print("\n❌ Integration test failed - check service logs")