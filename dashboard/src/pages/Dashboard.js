import React, { useEffect, useState } from "react";
import { OverviewCard, ServiceStatus, RecentActivity, MetricsGrid } from "../components/Dashboard";

const servicePorts = [
  { name: "Agent Service", port: 8001 },
  { name: "Workflow Service", port: 8002 },
  { name: "Communication Service", port: 8004 }
];

const fetchServiceHealth = async (port) => {
  const res = await fetch(`http://localhost:${port}/health`);
  if (!res.ok) throw new Error(res.statusText);
  return res.json();
};

const Dashboard = () => {
  const [services, setServices] = useState([]);
  const [metrics, setMetrics] = useState({
    activeAgents: 0,
    runningWorkflows: 0,
    queuedTasks: 0
  });

  useEffect(() => {
    // Fetch service health
    Promise.all(
      servicePorts.map(async (svc) => {
        try {
          const health = await fetchServiceHealth(svc.port);
          return { ...svc, status: health.status || "unknown" };
        } catch {
          return { ...svc, status: "unreachable" };
        }
      })
    ).then(setServices);

    // Fetch metrics
    const fetchMetrics = async () => {
      try {
        // Active Agents
        const agentsRes = await fetch("http://localhost:8001/agents/");
        const agents = agentsRes.ok ? await agentsRes.json() : [];
        const activeAgents = Array.isArray(agents) ? agents.length : (agents.count || 0);

        // Running Workflows
        const workflowsRes = await fetch("http://localhost:8002/workflows/");
        const workflows = workflowsRes.ok ? await workflowsRes.json() : [];
        // Adjust the filter below to match your actual running status key/value
        const runningWorkflows = Array.isArray(workflows)
          ? workflows.filter(wf => wf.status === "running").length
          : (workflows.running_count || 0);

        // Queued Tasks (Executions)
        const executionsRes = await fetch("http://localhost:8002/executions/");
        const executions = executionsRes.ok ? await executionsRes.json() : [];
        // Adjust the filter below to match your actual queued status key/value
        const queuedTasks = Array.isArray(executions)
          ? executions.filter(exec => exec.status === "queued").length
          : (executions.queued_count || 0);

        setMetrics({
          activeAgents,
          runningWorkflows,
          queuedTasks
        });
      } catch (e) {
        setMetrics({
          activeAgents: 0,
          runningWorkflows: 0,
          queuedTasks: 0
        });
      }
    };

    fetchMetrics();
  }, []);

  const mockActivity = [
    "Workflow #123 started",
    "Agent Alpha registered",
    "Alert: High CPU usage",
    "Workflow #122 completed"
  ];

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "2rem" }}>
      <div style={{ display: "flex", gap: "2rem" }}>
        <OverviewCard title="Active Agents" value={metrics.activeAgents} />
        <OverviewCard title="Running Workflows" value={metrics.runningWorkflows} />
        <OverviewCard title="Queued Tasks" value={metrics.queuedTasks} />
      </div>
      <div style={{ display: "flex", gap: "2rem" }}>
        <div style={{ flex: 2 }}>
          <h2>Service Status</h2>
          {services.map((s, i) => (
            <ServiceStatus key={i} name={s.name} status={s.status} />
          ))}
        </div>
        <div style={{ flex: 3 }}>
          <RecentActivity activities={mockActivity} />
        </div>
      </div>
      {/* You can keep MetricsGrid for other metrics if needed */}
    </div>
  );
};

export default Dashboard; 