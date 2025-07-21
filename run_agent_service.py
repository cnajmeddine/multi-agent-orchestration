#!/usr/bin/env python3
import sys
import os

# Add the project root to Python path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

if __name__ == "__main__":
    import uvicorn
    from services.agent_service.main import app
    
    uvicorn.run(
        app,
        host="0.0.0.0", 
        port=8001,
        reload=False,  # Set to True for development
        log_level="info"
    )