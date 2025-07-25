# run_monitoring_service.py
#!/usr/bin/env python3
import sys
import os

project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

if __name__ == "__main__":
    import uvicorn
    from services.monitoring_service.main import app
    
    uvicorn.run(app, host="0.0.0.0", port=8003, log_level="info")