import React from "react";

const MetricsChart = ({ data }) => (
  <div style={{ background: "#fff", borderRadius: 8, padding: "1.5rem 1rem", minHeight: 180 }}>
    <div style={{ fontWeight: "bold", fontSize: "1.1rem", color: "#1976d2" }}>Metrics Chart</div>
    <div style={{ color: "#888", fontSize: "0.95rem", marginTop: "1rem" }}>
      {/* Placeholder for chart - integrate chart library here */}
      {data ? "[Chart would render here]" : "No data available."}
    </div>
  </div>
);

export default MetricsChart; 