# minimal_comm_service.py - Minimal version for testing
import sys
import os
from fastapi import FastAPI
import uvicorn

# Add project root to path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

# Create minimal app first
app = FastAPI(
    title="AI Communication Service (Minimal)",
    description="Minimal version for testing",
    version="1.0.0"
)

@app.get("/")
async def root():
    return {
        "service": "communication-service-minimal",
        "version": "1.0.0",
        "status": "running",
        "message": "Minimal version is working!"
    }

@app.get("/health/")
async def health_check():
    return {
        "status": "healthy",
        "service": "communication-service-minimal"
    }

@app.get("/test")
async def test_endpoint():
    return {
        "message": "Test endpoint working",
        "timestamp": "2025-07-22T14:00:00Z"
    }

if __name__ == "__main__":
    print("🚀 Starting minimal communication service...")
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8004,
        log_level="info"
    )