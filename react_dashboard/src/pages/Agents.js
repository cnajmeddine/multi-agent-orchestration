import React from "react";
import { AgentList } from "../components/Agents";

const mockAgents = [
  { id: "agent-1", name: "Agent Alpha", status: "active" },
  { id: "agent-2", name: "Agent Beta", status: "active" },
  { id: "agent-3", name: "Agent Gamma", status: "inactive" }
];

const Agents = () => (
  <div>
    <h2>Agents</h2>
    <AgentList agents={mockAgents} />
  </div>
);

export default Agents; 