import React from "react";

const MetricsGrid = ({ metrics }) => (
  <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))", gap: "1.5rem" }}>
    {metrics.map((metric, i) => (
      <div key={i} style={{ background: "#fff", borderRadius: 8, padding: "1.5rem 1rem", textAlign: "center" }}>
        <div style={{ fontSize: "1.1rem", color: "#888" }}>{metric.label}</div>
        <div style={{ fontSize: "2rem", fontWeight: "bold", marginTop: "0.5rem" }}>{metric.value}</div>
      </div>
    ))}
  </div>
);

export default MetricsGrid; 