import React from "react";
import WorkflowCard from "./WorkflowCard";

const WorkflowList = ({ workflows }) => (
  <div style={{ display: "flex", flexWrap: "wrap", gap: "1.5rem" }}>
    {workflows && workflows.length > 0 ? (
      workflows.map((wf) => <WorkflowCard key={wf.id} workflow={wf} />)
    ) : (
      <div style={{ color: "#888" }}>No workflows found.</div>
    )}
  </div>
);

export default WorkflowList; 