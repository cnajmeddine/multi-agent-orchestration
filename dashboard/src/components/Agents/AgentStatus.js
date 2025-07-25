import React from "react";
import StatusBadge from "../Common/StatusBadge";

const AgentStatus = ({ status }) => (
  <div style={{ marginTop: "0.5rem" }}>
    <StatusBadge status={status} />
  </div>
);

export default AgentStatus; 