import React from "react";

const RecentActivity = ({ activities }) => (
  <div style={{ background: "#fff", borderRadius: 8, padding: "1rem 1.5rem", minHeight: 120 }}>
    <h3 style={{ margin: 0, fontSize: "1.1rem", color: "#1976d2" }}>Recent Activity</h3>
    <ul style={{ margin: 0, padding: 0, listStyle: "none" }}>
      {activities && activities.length > 0 ? (
        activities.map((a, i) => (
          <li key={i} style={{ padding: "0.5rem 0", borderBottom: "1px solid #f0f0f0" }}>
            {a}
          </li>
        ))
      ) : (
        <li style={{ color: "#888", padding: "0.5rem 0" }}>No recent activity.</li>
      )}
    </ul>
  </div>
);

export default RecentActivity; 