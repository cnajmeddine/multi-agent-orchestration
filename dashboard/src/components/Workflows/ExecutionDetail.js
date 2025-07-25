import React from "react";

const ExecutionDetail = ({ execution }) => (
  <div style={{ background: "#fff", borderRadius: 8, padding: "1.5rem 1rem", minWidth: 220 }}>
    <div style={{ fontWeight: "bold", fontSize: "1.1rem" }}>Execution: {execution.id}</div>
    <div>Status: {execution.status}</div>
    <div>Started: {execution.startedAt}</div>
    <div>Ended: {execution.endedAt}</div>
  </div>
);

export default ExecutionDetail; 