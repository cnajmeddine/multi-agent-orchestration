import React from "react";
import { AlertsList, MetricsChart, CountersView } from "../components/Monitoring";

const mockAlerts = [
  "High CPU usage on Agent Beta",
  "Workflow #123 failed",
  "Agent Gamma disconnected"
];

const mockCounters = {
  "Errors": 2,
  "Warnings": 5,
  "Success": 42
};

const Monitoring = () => (
  <div>
    <h2>Monitoring</h2>
    <div style={{ display: "flex", gap: "2rem" }}>
      <div style={{ flex: 2 }}>
        <AlertsList alerts={mockAlerts} />
        <CountersView counters={mockCounters} />
      </div>
      <div style={{ flex: 3 }}>
        <MetricsChart data={null} />
      </div>
    </div>
  </div>
);

export default Monitoring; 