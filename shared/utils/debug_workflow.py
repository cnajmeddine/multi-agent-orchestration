# simple_debug.py - Standalone debug script
import asyncio
import httpx
import json

async def debug_latest_failures():
    """Debug the most recent failed executions."""
    
    async with httpx.AsyncClient() as client:
        try:
            print("🔍 Getting failed executions...")
            response = await client.get("http://localhost:8002/executions/?status=failed")
            
            if response.status_code == 200:
                executions = response.json()
                
                if executions:
                    print(f"Found {len(executions)} failed executions")
                    
                    # Debug the most recent failure
                    latest = executions[0]
                    execution_id = latest['execution_id']
                    
                    print(f"\n🔍 DEBUGGING EXECUTION: {execution_id}")
                    
                    # Get detailed logs
                    logs_response = await client.get(f"http://localhost:8002/executions/{execution_id}/logs")
                    
                    if logs_response.status_code == 200:
                        logs = logs_response.json()
                        
                        print(f"Workflow ID: {logs['workflow_id']}")
                        print(f"Overall Status: {logs['status']}")
                        print(f"Context: {json.dumps(logs['context'], indent=2)}")
                        
                        print("\n📋 STEP DETAILS:")
                        for i, step_log in enumerate(logs['step_logs']):
                            print(f"\n--- Step {i+1}: {step_log['step_id']} ---")
                            print(f"Status: {step_log['status']}")
                            
                            if step_log['input_data']:
                                print(f"Input: {json.dumps(step_log['input_data'], indent=2)}")
                            
                            if step_log['output_data']:
                                print(f"Output: {json.dumps(step_log['output_data'], indent=2)}")
                            
                            if step_log['error_message']:
                                print(f"❌ ERROR: {step_log['error_message']}")
                            
                            print(f"Agent: {step_log['agent_id']}")
                    else:
                        print(f"❌ Failed to get logs: {logs_response.status_code}")
                        print(logs_response.text)
                else:
                    print("✅ No failed executions found")
            else:
                print(f"❌ Failed to get executions: {response.status_code}")
                print(response.text)
                
        except Exception as e:
            print(f"❌ Error: {str(e)}")

async def test_agents():
    """Test agents directly."""
    
    async with httpx.AsyncClient() as client:
        print("\n🧪 TESTING AGENTS...")
        
        # Check available agents
        try:
            response = await client.get("http://localhost:8001/agents/")
            
            if response.status_code == 200:
                agents = response.json()
                print(f"Found {len(agents)} agents:")
                for agent in agents:
                    print(f"  - {agent['name']} ({agent['agent_type']}) - Status: {agent['status']}")
            else:
                print(f"❌ Failed to list agents: {response.status_code}")
                return
                
        except Exception as e:
            print(f"❌ Error listing agents: {str(e)}")
            return
        
        # Test text processor
        print("\n🔤 Testing text processor...")
        try:
            response = await client.post(
                "http://localhost:8001/agents/execute",
                json={
                    "agent_type": "text_processor",
                    "input_data": {
                        "task_type": "sentiment_analysis",
                        "text": "I'm really disappointed with the product quality."
                    }
                }
            )
            
            if response.status_code == 200:
                result = response.json()
                print(f"✅ Success: {result['success']}")
                if result['success']:
                    print(f"Output: {json.dumps(result['output_data'], indent=2)}")
                else:
                    print(f"Error: {result['error_message']}")
            else:
                print(f"❌ HTTP Error: {response.status_code}")
                print(response.text)
                
        except Exception as e:
            print(f"❌ Exception: {str(e)}")
        
        # Test data analyzer
        print("\n📊 Testing data analyzer...")
        try:
            test_data = [
                {"customer_id": 1, "age": 25, "purchase_amount": 150.50},
                {"customer_id": 2, "age": 34, "purchase_amount": 89.99}
            ]
            
            response = await client.post(
                "http://localhost:8001/agents/execute",
                json={
                    "agent_type": "data_analyzer",
                    "input_data": {
                        "task_type": "data_summary",
                        "data": test_data
                    }
                }
            )
            
            if response.status_code == 200:
                result = response.json()
                print(f"✅ Success: {result['success']}")
                if result['success']:
                    print(f"Output: {json.dumps(result['output_data'], indent=2)}")
                else:
                    print(f"Error: {result['error_message']}")
            else:
                print(f"❌ HTTP Error: {response.status_code}")
                print(response.text)
                
        except Exception as e:
            print(f"❌ Exception: {str(e)}")

async def test_simple_workflow():
    """Create and test a simple workflow."""
    
    async with httpx.AsyncClient() as client:
        print("\n🔧 Testing simple workflow...")
        
        # Create simple workflow
        simple_workflow = {
            "name": "Simple Test Workflow",
            "description": "Just sentiment analysis",
            "steps": [
                {
                    "name": "sentiment_test",
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
            ],
            "global_timeout": 300
        }
        
        try:
            # Create workflow
            response = await client.post(
                "http://localhost:8002/workflows/",
                json=simple_workflow
            )
            
            if response.status_code == 200:
                workflow = response.json()
                workflow_id = workflow['workflow_id']
                print(f"✅ Created simple workflow: {workflow_id}")
                
                # Execute it
                execution_response = await client.post(
                    f"http://localhost:8002/workflows/{workflow_id}/execute",
                    json={
                        "input_data": {
                            "test_message": "This is a positive message!"
                        }
                    }
                )
                
                if execution_response.status_code == 200:
                    execution = execution_response.json()
                    execution_id = execution['execution_id']
                    print(f"🚀 Started execution: {execution_id}")
                    
                    # Wait and check result
                    await asyncio.sleep(5)
                    
                    result_response = await client.get(
                        f"http://localhost:8002/executions/{execution_id}"
                    )
                    
                    if result_response.status_code == 200:
                        result = result_response.json()
                        print(f"Status: {result['status']}")
                        print(f"Context: {json.dumps(result['context'], indent=2)}")
                        
                        if result['status'] == 'failed':
                            # Get logs
                            logs_response = await client.get(
                                f"http://localhost:8002/executions/{execution_id}/logs"
                            )
                            if logs_response.status_code == 200:
                                logs = logs_response.json()
                                for step in logs['step_logs']:
                                    if step['error_message']:
                                        print(f"❌ Step Error: {step['error_message']}")
                    
                else:
                    print(f"❌ Failed to execute: {execution_response.status_code}")
                    print(execution_response.text)
            else:
                print(f"❌ Failed to create workflow: {response.status_code}")
                print(response.text)
                
        except Exception as e:
            print(f"❌ Error: {str(e)}")

async def main():
    """Run all debug checks."""
    await test_agents()
    await debug_latest_failures()
    await test_simple_workflow()

if __name__ == "__main__":
    asyncio.run(main())