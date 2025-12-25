import React from "react";
import { Link } from "react-router-dom";

export default function Dashboard({ progress }) {
  return (
    <div>
      <h2>Dashboard</h2>
      {progress.length === 0 ? (
        <p>No sessions yet. Complete an interview to see your progress.</p>
      ) : (
        <>
          <p style={{ color: "var(--muted)" }}>
            Showing {progress.length} session{progress.length > 1 ? "s" : ""}.
          </p>
          <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 14 }}>
            <thead>
              <tr>
                <th style={{ textAlign: "left", padding: 8 }}>Date</th>
                <th style={{ textAlign: "left", padding: 8 }}>Role</th>
                <th style={{ textAlign: "left", padding: 8 }}>Level</th>
                <th style={{ textAlign: "left", padding: 8 }}>Score</th>
              </tr>
            </thead>
            <tbody>
              {progress.map((s, idx) => (
                <tr key={idx} style={{ borderTop: "1px solid #e5e7eb" }}>
                  <td style={{ padding: 8 }}>
                    {new Date(s.date).toLocaleString()}
                  </td>
                  <td style={{ padding: 8 }}>{s.role || "-"}</td>
                  <td style={{ padding: 8 }}>{s.level}</td>
                  <td style={{ padding: 8 }}>{s.score}/10</td>
                </tr>
              ))}
            </tbody>
          </table>
        </>
      )}

      <div style={{ marginTop: 16 }}>
        <Link to="/interview">Do another interview</Link>
      </div>
    </div>
  );
}
