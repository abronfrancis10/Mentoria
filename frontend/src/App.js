import React, { useState } from "react";
import { Routes, Route, useNavigate } from "react-router-dom";

import Home from "./pages/Home";
import RoleSelection from "./pages/RoleSelection";
import Interview from "./pages/Interview";
import Results from "./pages/Results";
import Dashboard from "./pages/Dashboard";

export default function App() {
  const navigate = useNavigate();

  const [user, setUser] = useState(null); // simple fake login
  const [roleInfo, setRoleInfo] = useState(null); // { role, resumeName }
  const [lastResult, setLastResult] = useState(null); // { level, improvements, avoid, score }
  const [progress, setProgress] = useState([]); // list of sessions

  function handleLogin(userData) {
    setUser(userData);
    navigate("/role");
  }

  function handleRoleSelected(info) {
    setRoleInfo(info);
    navigate("/interview");
  }

  function handleInterviewComplete(result) {
    const session = {
      ...result,
      role: roleInfo?.role,
      date: new Date().toISOString(),
    };
    setLastResult(session);
    setProgress((prev) => [...prev, session]);
    navigate("/results");
  }

  return (
    <div className="container">
      <div className="card">
        {/* Simple header */}
        <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 16 }}>
          <div>
            <h1 style={{ marginBottom: 4 }}>Mentoria</h1>
            <p style={{ margin: 0, color: "var(--muted)" }}>
              AI Interview Trainer
            </p>
          </div>
          <div style={{ textAlign: "right", fontSize: 14 }}>
            {user ? (
              <>
                <div>Hi, {user.name || user.email}</div>
                <div style={{ color: "var(--muted)" }}>
                  {roleInfo ? `Role: ${roleInfo.role}` : "No role selected"}
                </div>
              </>
            ) : (
              <div style={{ color: "var(--muted)" }}>Not logged in</div>
            )}
          </div>
        </div>

        <Routes>
          <Route path="/" element={<Home onLogin={handleLogin} />} />
          <Route
            path="/role"
            element={<RoleSelection onNext={handleRoleSelected} />}
          />
          <Route
            path="/interview"
            element={
              <Interview
                roleInfo={roleInfo}
                onComplete={handleInterviewComplete}
              />
            }
          />
          <Route
            path="/results"
            element={<Results result={lastResult} />}
          />
          <Route
            path="/dashboard"
            element={<Dashboard progress={progress} />}
          />
        </Routes>
      </div>
    </div>
  );
}
