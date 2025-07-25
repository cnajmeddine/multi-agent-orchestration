import React from "react";

const ExecutionLogs = ({ logs }) => (
  <div style={{ background: "#fff", borderRadius: 8, padding: "1rem 1.5rem", minHeight: 120 }}>
    <h3 style={{ margin: 0, fontSize: "1.1rem", color: "#1976d2" }}>Execution Logs</h3>
    <pre style={{ fontSize: "0.95rem", color: "#333", background: "#f4f4f4", padding: "1rem", borderRadius: 4, overflowX: "auto" }}>
      {logs || "No logs available."}
    </pre>
  </div>
);

export default ExecutionLogs; 