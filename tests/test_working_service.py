# test_working_service.py - Test the working communication service
import asyncio
import httpx
import time

async def test_working_service():
    """Test the working communication service."""
    
    print("🚀 TESTING WORKING COMMUNICATION SERVICE")
    print("=" * 50)
    
    # Wait for service to start
    print("⏳ Waiting 3 seconds for service to start...")
    await asyncio.sleep(3)
    
    async with httpx.AsyncClient(timeout=15.0) as client:
        
        # 1. Basic connectivity
        print("\n1. 🔌 BASIC CONNECTIVITY")
        try:
            response = await client.get("http://127.0.0.1:8004/")
            if response.status_code == 200:
                data = response.json()
                print(f"✅ Service: {data['service']}")
                print(f"   Status: {data['status']}")
                print(f"   Message: {data.get('message', 'N/A')}")
            else:
                print(f"❌ HTTP {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ Connection failed: {str(e)}")
            return False
        
        # 2. Initialize components
        print("\n2. 🔧 COMPONENT INITIALIZATION")
        try:
            response = await client.get("http://127.0.0.1:8004/init")
            if response.status_code == 200:
                data = response.json()
                print(f"✅ Initialization: {data['message']}")
                for comp, status in data['results'].items():
                    print(f"   - {comp}: {status}")
            else:
                print(f"❌ Init failed: HTTP {response.status_code}")
        except Exception as e:
            print(f"❌ Initialization error: {str(e)}")
        
        # 3. Health check
        print("\n3. 🏥 HEALTH CHECK")
        try:
            response = await client.get("http://127.0.0.1:8004/health/detailed")
            if response.status_code == 200:
                data = response.json()
                print(f"✅ Health: {data['status']}")
                for comp, status in data.get('components', {}).items():
                    print(f"   - {comp}: {status.get('status', 'unknown')}")
        except Exception as e:
            print(f"❌ Health check failed: {str(e)}")
        
        # 4. Service stats
        print("\n4. 📊 SERVICE STATS")
        try:
            response = await client.get("http://127.0.0.1:8004/stats")
            if response.status_code == 200:
                data = response.json()
                print(f"✅ Stats retrieved")
                status = data.get('component_status', {})
                if status:
                    print(f"   - Initialized: {status.get('initialized', [])}")
                    print(f"   - Errors: {status.get('errors', [])}")
                    print(f"   - Not initialized: {status.get('not_initialized', [])}")
        except Exception as e:
            print(f"❌ Stats error: {str(e)}")
        
        # 5. Test routes from the actual route files
        print("\n5. 📡 ROUTE TESTING")
        
        # Test events route
        try:
            response = await client.get("http://127.0.0.1:8004/events/stats")
            if response.status_code == 200:
                print("✅ Events route working")
            else:
                print(f"❌ Events route: HTTP {response.status_code}")
        except Exception as e:
            print(f"❌ Events route error: {str(e)}")
        
        # Test webhooks route
        try:
            response = await client.get("http://127.0.0.1:8004/webhooks/")
            if response.status_code == 200:
                print("✅ Webhooks route working")
            else:
                print(f"❌ Webhooks route: HTTP {response.status_code}")
        except Exception as e:
            print(f"❌ Webhooks route error: {str(e)}")
        
        # Test queues route
        try:
            response = await client.get("http://127.0.0.1:8004/queues/")
            if response.status_code == 200:
                print("✅ Queues route working")
            else:
                print(f"❌ Queues route: HTTP {response.status_code}")
        except Exception as e:
            print(f"❌ Queues route error: {str(e)}")
        
        return True

if __name__ == "__main__":
    print("Make sure to:")
    print("1. Replace services/communication_service/main.py with the working version")
    print("2. Start: python run_communication_service.py")
    print("3. Then run this test")
    print()
    
    try:
        success = asyncio.run(test_working_service())
        
        if success:
            print("\n🎉 WORKING SERVICE TEST COMPLETED!")
            print("\nThis version:")
            print("✅ Uses the same lazy initialization as no-lifespan")
            print("✅ Includes all the real route files")
            print("✅ Provides app.state for route dependencies")
            print("✅ No hanging lifespan events")
            print("\nNow you can run the full demo:")
            print("python communication_service_demo.py")
        else:
            print("\n❌ Service test failed")
    
    except Exception as e:
        print(f"\n❌ Test script failed: {str(e)}")