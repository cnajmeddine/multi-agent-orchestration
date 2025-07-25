import React from "react";

const WorkflowCard = ({ workflow }) => (
  <div style={{ background: "#fff", borderRadius: 8, padding: "1.5rem 1rem", minWidth: 220 }}>
    <div style={{ fontWeight: "bold", fontSize: "1.1rem" }}>{workflow.name}</div>
    <div style={{ color: "#888", fontSize: "0.95rem" }}>ID: {workflow.id}</div>
    <div style={{ marginTop: "0.5rem" }}>Status: {workflow.status}</div>
  </div>
);

export default WorkflowCard; 