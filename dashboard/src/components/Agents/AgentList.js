import React from "react";
import AgentCard from "./AgentCard";

const AgentList = ({ agents }) => (
  <div style={{ display: "flex", flexWrap: "wrap", gap: "1.5rem" }}>
    {agents && agents.length > 0 ? (
      agents.map((agent) => <AgentCard key={agent.id} agent={agent} />)
    ) : (
      <div style={{ color: "#888" }}>No agents found.</div>
    )}
  </div>
);

export default AgentList; 