import React from "react";

const RefreshButton = ({ onClick, loading }) => (
  <button
    onClick={onClick}
    disabled={loading}
    style={{
      background: "#1976d2",
      color: "#fff",
      border: "none",
      borderRadius: 6,
      padding: "0.5rem 1.2rem",
      fontSize: "1rem",
      cursor: loading ? "not-allowed" : "pointer",
      marginLeft: 8
    }}
  >
    {loading ? "Refreshing..." : "Refresh"}
  </button>
);

export default RefreshButton; 