#!/usr/bin/env python3
# run_communication_service.py - Start the communication service
import sys
import os

# Add the project root to Python path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "services.communication_service.main:app",
        host="0.0.0.0", 
        port=8004,
        reload=False,  # Set to True for development
        log_level="info"
    )