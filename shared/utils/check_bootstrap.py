# check_bootstrap.py - Debug bootstrap status
import asyncio
import httpx
import json

async def check_bootstrap_status():
    """Check if bootstrap is working."""
    
    async with httpx.AsyncClient() as client:
        try:
            print("🔍 Checking agent service bootstrap...")
            
            # Check agent instances in bootstrap
            response = await client.get("http://localhost:8001/agents/debug/instances")
            
            if response.status_code == 200:
                data = response.json()
                print(f"Bootstrap instances: {data['total_instances']}")
                print(f"Instance IDs: {data['instance_ids']}")
                print(f"Instance types: {json.dumps(data['instance_types'], indent=2)}")
            else:
                print(f"❌ Failed to get bootstrap status: {response.status_code}")
                print(response.text)
            
            # Check Redis agent data
            print("\n🔍 Checking Redis agent registry...")
            response = await client.get("http://localhost:8001/health/detailed")
            
            if response.status_code == 200:
                health = response.json()
                registry_info = health.get('components', {}).get('agent_registry', {})
                print(f"Total agents in Redis: {registry_info.get('total_agents', 0)}")
                print(f"Agents by type: {registry_info.get('agents_by_type', {})}")
            else:
                print(f"❌ Failed to get health status: {response.status_code}")
            
            # Try to trigger bootstrap recovery
            print("\n🔄 Triggering agent recovery...")
            response = await client.post("http://localhost:8001/agents/bootstrap/recover")
            
            if response.status_code == 200:
                result = response.json()
                print(f"✅ Recovery result: {result['message']}")
                print(f"Recovered agents: {result['recovered_agents']}")
            else:
                print(f"❌ Recovery failed: {response.status_code}")
                print(response.text)
            
            # Check agents after recovery
            print("\n🔍 Checking agents after recovery...")
            response = await client.get("http://localhost:8001/agents/")
            
            if response.status_code == 200:
                agents = response.json()
                print(f"Found {len(agents)} agents after recovery:")
                for agent in agents:
                    print(f"  - {agent['name']} ({agent['agent_type']}) - Status: {agent['status']}")
                    print(f"    Load: {agent['current_load']}/{agent['max_concurrent_tasks']}")
            else:
                print(f"❌ Failed to list agents: {response.status_code}")
                
        except Exception as e:
            print(f"❌ Error: {str(e)}")

async def test_agent_after_recovery():
    """Test agent execution after recovery."""
    
    async with httpx.AsyncClient() as client:
        print("\n🧪 Testing agent execution after recovery...")
        
        try:
            response = await client.post(
                "http://localhost:8001/agents/execute",
                json={
                    "agent_type": "text_processor",
                    "input_data": {
                        "task_type": "sentiment_analysis",
                        "text": "This should work now!"
                    }
                }
            )
            
            if response.status_code == 200:
                result = response.json()
                print(f"✅ Agent execution: {result['success']}")
                if result['success']:
                    print(f"Output: {json.dumps(result['output_data'], indent=2)}")
                else:
                    print(f"Error: {result['error_message']}")
            else:
                print(f"❌ HTTP Error: {response.status_code}")
                print(response.text)
                
        except Exception as e:
            print(f"❌ Exception: {str(e)}")

if __name__ == "__main__":
    async def main():
        await check_bootstrap_status()
        await test_agent_after_recovery()
    
    asyncio.run(main())