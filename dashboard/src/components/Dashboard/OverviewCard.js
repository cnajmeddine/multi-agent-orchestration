import React from "react";

const OverviewCard = ({ title, value }) => (
  <div style={{
    background: "#fff",
    borderRadius: "8px",
    boxShadow: "0 1px 3px rgba(0,0,0,0.04)",
    padding: "1.5rem 2rem",
    minWidth: "180px",
    textAlign: "center"
  }}>
    <div style={{ fontSize: "1.1rem", color: "#888" }}>{title}</div>
    <div style={{ fontSize: "2rem", fontWeight: "bold", marginTop: "0.5rem" }}>{value}</div>
  </div>
);

export default OverviewCard; 