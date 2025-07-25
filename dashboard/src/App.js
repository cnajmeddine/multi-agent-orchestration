import React from "react";
import { BrowserRouter as Router, Routes, Route } from "react-router-dom";
import Layout from "./components/Layout/Layout";
import DashboardPage from "./pages/Dashboard";
import WorkflowsPage from "./pages/Workflows";
import AgentsPage from "./pages/Agents";
import MonitoringPage from "./pages/Monitoring";
import "./App.css";

function App() {
  return (
    <Router>
      <Layout>
        <Routes>
          <Route path="/" element={<DashboardPage />} />
          <Route path="/workflows" element={<WorkflowsPage />} />
          <Route path="/agents" element={<AgentsPage />} />
          <Route path="/monitoring" element={<MonitoringPage />} />
        </Routes>
      </Layout>
    </Router>
  );
}

export default App; 