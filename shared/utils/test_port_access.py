# test_port_access.py - Test if port 8004 is accessible
import socket
import requests
import time

def test_port_binding():
    """Test if port 8004 is available."""
    print("🔍 Testing port 8004...")
    
    try:
        # Try to bind to the port
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)
        result = sock.connect_ex(('127.0.0.1', 8004))
        sock.close()
        
        if result == 0:
            print("✅ Port 8004 is open and something is listening")
            return True
        else:
            print("❌ Port 8004 is not accessible")
            return False
            
    except Exception as e:
        print(f"❌ Port test failed: {str(e)}")
        return False

def test_direct_connection():
    """Test direct HTTP connection."""
    print("\n🌐 Testing HTTP connection...")
    
    urls_to_try = [
        "http://127.0.0.1:8004/",
        "http://localhost:8004/",
        "http://0.0.0.0:8004/"
    ]
    
    for url in urls_to_try:
        try:
            print(f"   Trying {url}...")
            response = requests.get(url, timeout=10)
            
            if response.status_code == 200:
                print(f"✅ Success! Service accessible at {url}")
                data = response.json()
                print(f"   Response: {data}")
                return True
            else:
                print(f"❌ HTTP {response.status_code} from {url}")
                
        except requests.exceptions.ConnectionError:
            print(f"❌ Connection refused: {url}")
        except requests.exceptions.Timeout:
            print(f"❌ Timeout: {url}")
        except Exception as e:
            print(f"❌ Error with {url}: {str(e)}")
    
    return False

def check_process_listening():
    """Check what's listening on port 8004."""
    print("\n🔍 Checking what's listening on port 8004...")
    
    try:
        import subprocess
        
        # Windows netstat command
        result = subprocess.run(
            ['netstat', '-an'], 
            capture_output=True, 
            text=True, 
            timeout=10
        )
        
        lines = result.stdout.split('\n')
        for line in lines:
            if ':8004' in line:
                print(f"   {line.strip()}")
                
    except Exception as e:
        print(f"❌ Could not check listening processes: {str(e)}")

def test_with_curl():
    """Test with curl if available."""
    print("\n🔧 Testing with curl...")
    
    try:
        import subprocess
        
        result = subprocess.run(
            ['curl', '-v', 'http://localhost:8004/'], 
            capture_output=True, 
            text=True, 
            timeout=10
        )
        
        if result.returncode == 0:
            print("✅ Curl successful")
            print(f"   Output: {result.stdout[:200]}")
        else:
            print("❌ Curl failed")
            print(f"   Error: {result.stderr[:200]}")
            
    except FileNotFoundError:
        print("❌ Curl not available")
    except Exception as e:
        print(f"❌ Curl test failed: {str(e)}")

if __name__ == "__main__":
    print("🔧 PORT 8004 ACCESSIBILITY TEST")
    print("=" * 40)
    
    # Wait a moment for any service to start
    print("⏳ Waiting 3 seconds for service to start...")
    time.sleep(3)
    
    test_port_binding()
    test_direct_connection()
    check_process_listening()
    test_with_curl()
    
    print("\n💡 Suggestions:")
    print("1. Try the minimal service: python minimal_comm_service.py")
    print("2. Check Windows Firewall settings")
    print("3. Try a different port (8005, 8006, etc.)")
    print("4. Check if antivirus is blocking the connection")