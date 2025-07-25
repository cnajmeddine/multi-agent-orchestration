# services/monitoring_service/main.py
# Real-time monitoring service with metrics collection and alerting

import asyncio
import logging
import time
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field
import httpx
import json
from collections import defaultdict, deque
from fastapi.middleware.cors import CORSMiddleware

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="AI Workflow Monitoring Service",
    description="Real-time monitoring, metrics, and alerting for AI workflows",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Models
class MetricPoint(BaseModel):
    timestamp: datetime
    value: float
    labels: Dict[str, str] = Field(default_factory=dict)

class Alert(BaseModel):
    alert_id: str
    severity: str  # "critical", "warning", "info"
    title: str
    description: str
    service: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    resolved_at: Optional[datetime] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)

class ServiceHealth(BaseModel):
    service_name: str
    status: str  # "healthy", "degraded", "unhealthy"
    last_check: datetime
    response_time: float
    error_count: int
    uptime_percentage: float

# Global state
class MonitoringState:
    def __init__(self):
        # Metrics storage (in-memory for demo, use TimeSeries DB in production)
        self.metrics: Dict[str, deque] = defaultdict(lambda: deque(maxlen=1000))
        
        # Active alerts
        self.alerts: Dict[str, Alert] = {}
        
        # Service health tracking
        self.service_health: Dict[str, ServiceHealth] = {}
        
        # Performance counters
        self.counters = {
            "workflows_started": 0,
            "workflows_completed": 0,
            "workflows_failed": 0,
            "steps_executed": 0,
            "agents_called": 0,
            "errors_total": 0
        }
        
        # Recent events for dashboard
        self.recent_events: deque = deque(maxlen=100)

state = MonitoringState()

# Metrics Collection
@app.post("/metrics/record")
async def record_metric(metric_name: str, value: float, labels: Dict[str, str] = None):
    """Record a metric point."""
    try:
        point = MetricPoint(
            timestamp=datetime.utcnow(),
            value=value,
            labels=labels or {}
        )
        
        state.metrics[metric_name].append(point)
        logger.debug(f"Recorded metric {metric_name}: {value}")
        
        # Check for alert conditions
        await check_metric_alerts(metric_name, value, labels or {})
        
        return {"status": "recorded", "metric": metric_name, "value": value}
        
    except Exception as e:
        logger.error(f"Failed to record metric: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/metrics/{metric_name}")
async def get_metric_data(metric_name: str, hours: int = 1):
    """Get metric data for the last N hours."""
    try:
        if metric_name not in state.metrics:
            return {"metric": metric_name, "data": []}
        
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)
        
        recent_points = [
            {
                "timestamp": point.timestamp.isoformat(),
                "value": point.value,
                "labels": point.labels
            }
            for point in state.metrics[metric_name]
            if point.timestamp >= cutoff_time
        ]
        
        return {
            "metric": metric_name,
            "hours": hours,
            "data_points": len(recent_points),
            "data": recent_points
        }
        
    except Exception as e:
        logger.error(f"Failed to get metric data: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/metrics/summary")
async def get_metrics_summary():
    """Get summary of all metrics."""
    try:
        summary = {}
        
        for metric_name, points in state.metrics.items():
            if not points:
                continue
                
            values = [p.value for p in points]
            summary[metric_name] = {
                "count": len(values),
                "latest": values[-1] if values else None,
                "average": sum(values) / len(values) if values else 0,
                "min": min(values) if values else None,
                "max": max(values) if values else None,
                "last_updated": points[-1].timestamp.isoformat() if points else None
            }
        
        return summary
        
    except Exception as e:
        logger.error(f"Failed to get metrics summary: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# Performance Counters
@app.post("/counters/increment")
async def increment_counter(counter_name: str, increment: int = 1):
    """Increment a performance counter."""
    try:
        if counter_name in state.counters:
            state.counters[counter_name] += increment
        else:
            state.counters[counter_name] = increment
        
        # Record as metric too
        await record_metric(f"counter_{counter_name}", state.counters[counter_name])
        
        return {"counter": counter_name, "value": state.counters[counter_name]}
        
    except Exception as e:
        logger.error(f"Failed to increment counter: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/counters")
async def get_counters():
    """Get all performance counters."""
    return state.counters

# Alert Management
@app.post("/alerts")
async def create_alert(alert: Alert):
    """Create a new alert."""
    try:
        state.alerts[alert.alert_id] = alert
        
        # Add to recent events
        state.recent_events.append({
            "type": "alert_created",
            "timestamp": alert.created_at.isoformat(),
            "data": {
                "alert_id": alert.alert_id,
                "severity": alert.severity,
                "title": alert.title,
                "service": alert.service
            }
        })
        
        logger.warning(f"Alert created: {alert.title} ({alert.severity})")
        return {"status": "created", "alert_id": alert.alert_id}
        
    except Exception as e:
        logger.error(f"Failed to create alert: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/alerts/{alert_id}/resolve")
async def resolve_alert(alert_id: str):
    """Resolve an alert."""
    try:
        if alert_id not in state.alerts:
            raise HTTPException(status_code=404, detail="Alert not found")
        
        state.alerts[alert_id].resolved_at = datetime.utcnow()
        
        # Add to recent events
        state.recent_events.append({
            "type": "alert_resolved",
            "timestamp": datetime.utcnow().isoformat(),
            "data": {"alert_id": alert_id}
        })
        
        logger.info(f"Alert resolved: {alert_id}")
        return {"status": "resolved", "alert_id": alert_id}
        
    except Exception as e:
        logger.error(f"Failed to resolve alert: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/alerts")
async def get_alerts(active_only: bool = True):
    """Get alerts, optionally filtering to active only."""
    try:
        alerts = list(state.alerts.values())
        
        if active_only:
            alerts = [a for a in alerts if a.resolved_at is None]
        
        # Sort by creation time (newest first)
        alerts.sort(key=lambda x: x.created_at, reverse=True)
        
        return {"alerts": alerts, "count": len(alerts)}
        
    except Exception as e:
        logger.error(f"Failed to get alerts: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# Service Health Monitoring
@app.post("/health/check")
async def check_service_health(service_name: str, url: str):
    """Check health of a service."""
    try:
        start_time = time.time()
        
        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                response = await client.get(f"{url}/health")
                response_time = time.time() - start_time
                
                if response.status_code == 200:
                    status = "healthy"
                    error_count = 0
                else:
                    status = "degraded"
                    error_count = 1
                    
            except Exception as e:
                response_time = time.time() - start_time
                status = "unhealthy"
                error_count = 1
                logger.warning(f"Health check failed for {service_name}: {str(e)}")
        
        # Update service health
        if service_name in state.service_health:
            # Calculate uptime percentage (simple moving average)
            old_health = state.service_health[service_name]
            if status == "healthy":
                uptime = min(old_health.uptime_percentage + 1, 100)
            else:
                uptime = max(old_health.uptime_percentage - 5, 0)
        else:
            uptime = 100 if status == "healthy" else 0
        
        state.service_health[service_name] = ServiceHealth(
            service_name=service_name,
            status=status,
            last_check=datetime.utcnow(),
            response_time=response_time,
            error_count=error_count,
            uptime_percentage=uptime
        )
        
        # Record metrics
        await record_metric(f"service_response_time", response_time, {"service": service_name})
        await record_metric(f"service_health", 1 if status == "healthy" else 0, {"service": service_name})
        
        return state.service_health[service_name]
        
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health/services")
async def get_services_health():
    """Get health status of all monitored services."""
    return {"services": list(state.service_health.values())}

# Dashboard API
@app.get("/dashboard/overview")
async def get_dashboard_overview():
    """Get dashboard overview data."""
    try:
        # Calculate some summary stats
        active_alerts_count = len([a for a in state.alerts.values() if a.resolved_at is None])
        critical_alerts = len([a for a in state.alerts.values() 
                             if a.resolved_at is None and a.severity == "critical"])
        
        healthy_services = len([s for s in state.service_health.values() 
                              if s.status == "healthy"])
        total_services = len(state.service_health)
        
        # Recent activity
        recent_workflows = state.counters.get("workflows_started", 0)
        success_rate = 0
        if state.counters.get("workflows_started", 0) > 0:
            success_rate = (state.counters.get("workflows_completed", 0) / 
                          state.counters.get("workflows_started", 1)) * 100
        
        return {
            "summary": {
                "active_alerts": active_alerts_count,
                "critical_alerts": critical_alerts,
                "healthy_services": healthy_services,
                "total_services": total_services,
                "workflow_success_rate": round(success_rate, 2),
                "total_workflows": recent_workflows
            },
            "counters": state.counters,
            "recent_events": list(state.recent_events)[-10:],  # Last 10 events
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to get dashboard overview: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/dashboard/workflows")
async def get_workflow_dashboard():
    """Get workflow-specific dashboard data."""
    try:
        # Get workflow metrics for the last hour
        workflow_metrics = {}
        for metric_name in ["workflow_execution_time", "step_execution_time", "agent_response_time"]:
            if metric_name in state.metrics:
                recent_points = [p for p in state.metrics[metric_name] 
                               if p.timestamp >= datetime.utcnow() - timedelta(hours=1)]
                if recent_points:
                    values = [p.value for p in recent_points]
                    workflow_metrics[metric_name] = {
                        "average": sum(values) / len(values),
                        "count": len(values),
                        "latest": values[-1]
                    }
        
        return {
            "metrics": workflow_metrics,
            "counters": {
                "workflows_started": state.counters.get("workflows_started", 0),
                "workflows_completed": state.counters.get("workflows_completed", 0),
                "workflows_failed": state.counters.get("workflows_failed", 0),
                "steps_executed": state.counters.get("steps_executed", 0)
            }
        }
        
    except Exception as e:
        logger.error(f"Failed to get workflow dashboard: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# Event Processing
@app.post("/events/process")
async def process_event(event_data: Dict[str, Any]):
    """Process incoming events from other services."""
    try:
        event_type = event_data.get("event_type", "unknown")
        source_service = event_data.get("source_service", "unknown")
        payload = event_data.get("payload", {})
        
        # Update counters based on event type
        if event_type == "workflow.started":
            await increment_counter("workflows_started")
        elif event_type == "workflow.completed":
            await increment_counter("workflows_completed")
        elif event_type == "workflow.failed":
            await increment_counter("workflows_failed")
            
            # Create alert for failed workflow
            await create_alert(Alert(
                alert_id=f"workflow_failed_{datetime.utcnow().timestamp()}",
                severity="warning",
                title="Workflow Execution Failed",
                description=f"Workflow failed: {payload.get('error', 'Unknown error')}",
                service=source_service,
                metadata=payload
            ))
        elif event_type == "step.completed":
            await increment_counter("steps_executed")
        elif event_type == "agent.called":
            await increment_counter("agents_called")
        
        # Record timing metrics if available
        if "execution_time" in payload:
            metric_name = f"{event_type}_time"
            await record_metric(metric_name, float(payload["execution_time"]))
        
        # Add to recent events
        state.recent_events.append({
            "type": "service_event",
            "timestamp": datetime.utcnow().isoformat(),
            "data": {
                "event_type": event_type,
                "source_service": source_service,
                "payload": payload
            }
        })
        
        return {"status": "processed", "event_type": event_type}
        
    except Exception as e:
        logger.error(f"Failed to process event: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# Alert condition checking
async def check_metric_alerts(metric_name: str, value: float, labels: Dict[str, str]):
    """Check if metric value triggers any alerts."""
    try:
        # Define some basic alert conditions
        alert_conditions = {
            "workflow_execution_time": {"threshold": 300, "condition": "gt", "severity": "warning"},
            "agent_response_time": {"threshold": 30, "condition": "gt", "severity": "warning"},
            "error_rate": {"threshold": 0.1, "condition": "gt", "severity": "critical"},
            "service_health": {"threshold": 0, "condition": "eq", "severity": "critical"}
        }
        
        if metric_name in alert_conditions:
            condition = alert_conditions[metric_name]
            threshold = condition["threshold"]
            
            should_alert = False
            if condition["condition"] == "gt" and value > threshold:
                should_alert = True
            elif condition["condition"] == "lt" and value < threshold:
                should_alert = True
            elif condition["condition"] == "eq" and value == threshold:
                should_alert = True
            
            if should_alert:
                alert_id = f"{metric_name}_alert_{datetime.utcnow().timestamp()}"
                await create_alert(Alert(
                    alert_id=alert_id,
                    severity=condition["severity"],
                    title=f"Metric Alert: {metric_name}",
                    description=f"{metric_name} value {value} exceeds threshold {threshold}",
                    service="monitoring-service",
                    metadata={"metric": metric_name, "value": value, "threshold": threshold}
                ))
        
    except Exception as e:
        logger.error(f"Alert condition check failed: {str(e)}")

# Background tasks
async def periodic_health_checks():
    """Periodically check service health."""
    services_to_check = [
        {"name": "agent-service", "url": "http://localhost:8001"},
        {"name": "workflow-service", "url": "http://localhost:8002"},
        {"name": "communication-service", "url": "http://localhost:8004"}
    ]
    
    while True:
        try:
            for service in services_to_check:
                await check_service_health(service["name"], service["url"])
            
            await asyncio.sleep(30)  # Check every 30 seconds
            
        except Exception as e:
            logger.error(f"Periodic health check failed: {str(e)}")
            await asyncio.sleep(60)  # Wait longer on error

# Startup event
@app.on_event("startup")
async def startup_event():
    """Start background tasks."""
    asyncio.create_task(periodic_health_checks())
    logger.info("Monitoring service started with background health checks")

@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "service": "monitoring-service",
        "version": "1.0.0",
        "status": "running",
        "features": [
            "Real-time metrics collection",
            "Alert management",
            "Service health monitoring", 
            "Dashboard APIs",
            "Event processing"
        ]
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8003, log_level="info")