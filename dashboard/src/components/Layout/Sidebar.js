import React from "react";
import { NavLink } from "react-router-dom";

const Sidebar = () => (
  <aside style={{
    width: "220px",
    background: "#fff",
    borderRight: "1px solid #e5e7eb",
    minHeight: "100vh",
    padding: "2rem 0"
  }}>
    <nav style={{ display: "flex", flexDirection: "column", gap: "1.5rem" }}>
      <NavLink to="/" style={({ isActive }) => ({ color: isActive ? "#1976d2" : "#222", textDecoration: "none", fontWeight: isActive ? "bold" : "normal", padding: "0.5rem 2rem" })} end>
        Dashboard
      </NavLink>
      <NavLink to="/workflows" style={({ isActive }) => ({ color: isActive ? "#1976d2" : "#222", textDecoration: "none", fontWeight: isActive ? "bold" : "normal", padding: "0.5rem 2rem" })}>
        Workflows
      </NavLink>
      <NavLink to="/agents" style={({ isActive }) => ({ color: isActive ? "#1976d2" : "#222", textDecoration: "none", fontWeight: isActive ? "bold" : "normal", padding: "0.5rem 2rem" })}>
        Agents
      </NavLink>
      <NavLink to="/monitoring" style={({ isActive }) => ({ color: isActive ? "#1976d2" : "#222", textDecoration: "none", fontWeight: isActive ? "bold" : "normal", padding: "0.5rem 2rem" })}>
        Monitoring
      </NavLink>
    </nav>
  </aside>
);

export default Sidebar; 