import React, { useEffect, useState } from "react";
import { OverviewCard, ServiceStatus, RecentActivity, MetricsGrid } from "../components/Dashboard";
import ApiService from "../services/api";

const servicePorts = [
  { name: "Agent Service", port: 8001 },
  { name: "Workflow Service", port: 8002 },
  { name: "Monitoring Service", port: 8003 },
  { name: "Communication Service", port: 8004 }
];

const Dashboard = () => {
  const [services, setServices] = useState([]);
  const [metrics, setMetrics] = useState([
    { label: "Active Agents", value: 0 },
    { label: "Total Workflows", value: 0 },
    { label: "Running Executions", value: 0 },
    { label: "System Alerts", value: 0 }
  ]);
  const [recentActivity, setRecentActivity] = useState([]);

  const fetchServiceHealth = async (port) => {
    try {
      const res = await fetch(`http://localhost:${port}/`);
      if (!res.ok) throw new Error(res.statusText);
      const data = await res.json();
      return data.status || "unknown";
    } catch {
      return "unreachable";
    }
  };

  const fetchMetrics = async () => {
    try {
      // Get agents count
      const agents = await ApiService.getAgents();
      const activeAgents = agents.filter(a => a.status === 'idle' || a.status === 'busy').length;

      // Get workflows count
      const workflows = await ApiService.getWorkflows();

      // Get running executions
      const runningExecutions = await ApiService.getExecutions('running');

      // Get monitoring overview for recent activity
      const overview = await ApiService.getDashboardOverview();

      setMetrics([
        { label: "Active Agents", value: activeAgents },
        { label: "Total Workflows", value: workflows.length },
        { label: "Running Executions", value: runningExecutions.length },
        { label: "System Alerts", value: overview.summary?.active_alerts || 0 }
      ]);

      // Set recent activity from monitoring
      if (overview.recent_events) {
        const activities = overview.recent_events.slice(0, 4).map(event => {
          if (event.type === 'service_event') {
            return `${event.data.event_type} from ${event.data.source_service}`;
          }
          return `${event.type}: ${JSON.stringify(event.data).slice(0, 50)}...`;
        });
        setRecentActivity(activities);
      }

    } catch (error) {
      console.error('Failed to fetch metrics:', error);
    }
  };

  useEffect(() => {
    // Fetch service health
    Promise.all(
      servicePorts.map(async (svc) => {
        const status = await fetchServiceHealth(svc.port);
        return { ...svc, status };
      })
    ).then(setServices);

    // Fetch real metrics
    fetchMetrics();

    // Set up polling every 5 seconds
    const interval = setInterval(fetchMetrics, 5000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "2rem" }}>
      <div style={{ display: "flex", gap: "2rem" }}>
        {metrics.map((m, i) => (
          <OverviewCard key={i} title={m.label} value={m.value} />
        ))}
      </div>
      <div style={{ display: "flex", gap: "2rem" }}>
        <div style={{ flex: 2 }}>
          <h2>Service Status</h2>
          {services.map((s, i) => (
            <ServiceStatus key={i} name={s.name} status={s.status} />
          ))}
        </div>
        <div style={{ flex: 3 }}>
          <RecentActivity activities={recentActivity} />
        </div>
      </div>
      <div>
        <h2>Metrics</h2>
        <MetricsGrid metrics={metrics} />
      </div>
    </div>
  );
};

export default Dashboard;