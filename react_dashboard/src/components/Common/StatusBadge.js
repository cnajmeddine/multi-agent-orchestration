import React from "react";

const getColor = (status) => {
  switch ((status || "").toLowerCase()) {
    case "healthy":
    case "active":
    case "running":
    case "success":
      return "#43a047";
    case "unhealthy":
    case "failed":
    case "error":
      return "#d32f2f";
    case "pending":
    case "processing":
      return "#ffa000";
    default:
      return "#888";
  }
};

const StatusBadge = ({ status }) => (
  <span style={{
    display: "inline-block",
    minWidth: 70,
    padding: "0.25rem 0.75rem",
    borderRadius: 12,
    background: getColor(status),
    color: "#fff",
    fontWeight: 500,
    fontSize: "0.95rem",
    textAlign: "center"
  }}>
    {status}
  </span>
);

export default StatusBadge; 