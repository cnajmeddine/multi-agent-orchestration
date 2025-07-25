import React from "react";
import { WorkflowList } from "../components/Workflows";

const mockWorkflows = [
  { id: "wf-1", name: "Data Pipeline", status: "running" },
  { id: "wf-2", name: "Model Training", status: "completed" },
  { id: "wf-3", name: "Report Generation", status: "failed" }
];

const Workflows = () => (
  <div>
    <h2>Workflows</h2>
    <WorkflowList workflows={mockWorkflows} />
  </div>
);

export default Workflows; 