import React from "react";

const CountersView = ({ counters }) => (
  <div style={{ display: "flex", gap: "1.5rem" }}>
    {counters && Object.keys(counters).length > 0 ? (
      Object.entries(counters).map(([key, value]) => (
        <div key={key} style={{ background: "#fff", borderRadius: 8, padding: "1.5rem 1rem", minWidth: 120, textAlign: "center" }}>
          <div style={{ fontSize: "1.1rem", color: "#888" }}>{key}</div>
          <div style={{ fontSize: "2rem", fontWeight: "bold", marginTop: "0.5rem" }}>{value}</div>
        </div>
      ))
    ) : (
      <div style={{ color: "#888" }}>No counters available.</div>
    )}
  </div>
);

export default CountersView; 