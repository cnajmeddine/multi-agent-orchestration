import React from "react";
import Header from "./Header";
import Sidebar from "./Sidebar";

const Layout = ({ children }) => (
  <div style={{ display: "flex", flexDirection: "column", minHeight: "100vh" }}>
    <Header />
    <div style={{ display: "flex", flex: 1 }}>
      <Sidebar />
      <main style={{ flex: 1, padding: "2rem", background: "#f7f9fb" }}>
        {children}
      </main>
    </div>
  </div>
);

export default Layout; 