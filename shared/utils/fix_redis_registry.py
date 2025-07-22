# fix_redis_registry.py - Fix broken Redis registry
import asyncio
import httpx
import redis
import json
from datetime import datetime

async def diagnose_redis_issue():
    """Diagnose what's wrong with Redis registry."""
    
    # Connect to Redis directly
    redis_client = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)
    
    print("🔍 DIAGNOSING REDIS REGISTRY...")
    
    try:
        # Check if Redis is working
        redis_client.ping()
        print("✅ Redis connection working")
        
        # Check active agents set
        active_agents = redis_client.smembers("agents:active")
        print(f"Active agents set: {active_agents}")
        
        # Check each agent's data
        for agent_id in active_agents:
            agent_key = f"agent:{agent_id}"
            agent_data = redis_client.hgetall(agent_key)
            print(f"\nAgent {agent_id}:")
            print(f"  Raw data: {agent_data}")
            
            if agent_data:
                agent_type = agent_data.get('agent_type')
                print(f"  Type: {agent_type}")
                
                # Check type set
                type_set_key = f"agents:type:{agent_type}"
                type_members = redis_client.smembers(type_set_key)
                print(f"  Type set '{type_set_key}': {type_members}")
                
                # Check load set
                load_key = f"agents:load:{agent_type}"
                load_members = redis_client.zrange(load_key, 0, -1, withscores=True)
                print(f"  Load set '{load_key}': {load_members}")
        
        # Check all Redis keys related to agents
        agent_keys = redis_client.keys("agent*")
        print(f"\nAll agent-related keys: {agent_keys}")
        
        # Get registry stats via API
        async with httpx.AsyncClient() as client:
            response = await client.get("http://localhost:8001/health/detailed")
            if response.status_code == 200:
                health = response.json()
                registry_info = health.get('components', {}).get('agent_registry', {})
                print(f"\nAPI Registry stats:")
                print(f"  Total agents: {registry_info.get('total_agents', 0)}")
                print(f"  Agents by type: {registry_info.get('agents_by_type', {})}")
                print(f"  Heartbeat count: {registry_info.get('heartbeat_count', 0)}")
        
    except Exception as e:
        print(f"❌ Redis diagnosis failed: {str(e)}")

async def fix_registry():
    """Fix the broken registry by re-registering agents."""
    
    redis_client = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)
    
    print("\n🔧 FIXING REDIS REGISTRY...")
    
    try:
        # Get bootstrap instances
        async with httpx.AsyncClient() as client:
            response = await client.get("http://localhost:8001/agents/debug/instances")
            
            if response.status_code != 200:
                print("❌ Can't get bootstrap instances")
                return
            
            bootstrap_data = response.json()
            instance_ids = bootstrap_data['instance_ids']
            instance_types = bootstrap_data['instance_types']
            
            print(f"Found {len(instance_ids)} instances to fix")
            
            # Clear broken registry data
            print("🧹 Cleaning broken registry data...")
            redis_client.delete("agents:active")
            
            # Get all type sets and clear them
            for agent_type in ['text_processor', 'data_analyzer']:
                redis_client.delete(f"agents:type:{agent_type}")
                redis_client.delete(f"agents:load:{agent_type}")
            
            # Re-register each agent
            for agent_id in instance_ids:
                agent_type_class = instance_types[agent_id]
                
                # Map class names to agent types
                if agent_type_class == "TextProcessingAgent":
                    agent_type = "text_processor"
                    capabilities = [
                        {
                            "name": "sentiment_analysis",
                            "description": "Analyze sentiment of text",
                            "input_types": ["text"],
                            "output_types": ["json"],
                            "max_concurrent_tasks": 5
                        }
                    ]
                elif agent_type_class == "DataAnalysisAgent":
                    agent_type = "data_analyzer"
                    capabilities = [
                        {
                            "name": "data_summary",
                            "description": "Generate summary statistics for datasets",
                            "input_types": ["json", "csv"],
                            "output_types": ["json"],
                            "max_concurrent_tasks": 3
                        }
                    ]
                else:
                    continue
                
                # Create agent metadata
                agent_data = {
                    'agent_id': agent_id,
                    'name': f"recovered-{agent_type}-{agent_id[:8]}",
                    'agent_type': agent_type,
                    'capabilities': json.dumps(capabilities),
                    'status': 'idle',
                    'current_load': '0',
                    'max_concurrent_tasks': '3',
                    'last_heartbeat': datetime.utcnow().isoformat(),
                    'created_at': datetime.utcnow().isoformat(),
                    'config': '{}'
                }
                
                # Store in Redis using the same pattern as agent_registry.py
                agent_key = f"agent:{agent_id}"
                redis_client.hset(agent_key, mapping=agent_data)
                
                # Add to sets
                redis_client.sadd("agents:active", agent_id)
                redis_client.sadd(f"agents:type:{agent_type}", agent_id)
                redis_client.zadd(f"agents:load:{agent_type}", {agent_id: 0})
                
                # Set expiration
                redis_client.expire(agent_key, 300)
                
                print(f"✅ Fixed agent {agent_id} ({agent_type})")
            
            # Verify fix
            print("\n🔍 Verifying fix...")
            response = await client.get("http://localhost:8001/agents/")
            
            if response.status_code == 200:
                agents = response.json()
                print(f"✅ Now found {len(agents)} agents:")
                for agent in agents:
                    print(f"  - {agent['name']} ({agent['agent_type']}) - Status: {agent['status']}")
            else:
                print(f"❌ Still broken: {response.status_code}")
    
    except Exception as e:
        print(f"❌ Fix failed: {str(e)}")

async def test_after_fix():
    """Test agent execution after fix."""
    
    async with httpx.AsyncClient() as client:
        print("\n🧪 TESTING AFTER FIX...")
        
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
        await diagnose_redis_issue()
        await fix_registry()
        await test_after_fix()
    
    asyncio.run(main())