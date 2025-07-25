import React from "react";
import AgentStatus from "./AgentStatus";

const AgentCard = ({ agent }) => (
  <div style={{ background: "#fff", borderRadius: 8, padding: "1.5rem 1rem", minWidth: 220 }}>
    <div style={{ fontWeight: "bold", fontSize: "1.1rem" }}>{agent.name}</div>
    <div style={{ color: "#888", fontSize: "0.95rem" }}>ID: {agent.id}</div>
    <AgentStatus status={agent.status} />
  </div>
);

export default AgentCard; 