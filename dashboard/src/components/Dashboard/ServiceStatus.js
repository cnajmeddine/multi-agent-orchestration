import React from "react";
import StatusBadge from "../Common/StatusBadge";

const ServiceStatus = ({ name, status }) => (
  <div style={{ display: "flex", alignItems: "center", gap: "1rem", marginBottom: "0.5rem" }}>
    <span style={{ minWidth: 120 }}>{name}</span>
    <StatusBadge status={status} />
  </div>
);

export default ServiceStatus; 