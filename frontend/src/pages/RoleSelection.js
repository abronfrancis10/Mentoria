import React, { useState } from "react";

const ROLES = [
  "Software Engineer",
  "Data Analyst",
  "Frontend Developer",
  "Backend Developer",
  "HR / Behavioral",
];

export default function RoleSelection({ onNext }) {
  const [role, setRole] = useState(ROLES[0]);
  const [resumeFile, setResumeFile] = useState(null);

  function handleSubmit(e) {
    e.preventDefault();
    onNext({
      role,
      resumeName: resumeFile ? resumeFile.name : null,
    });
  }

  return (
    <div>
      <h2>Select Role & Upload Resume</h2>

      <form onSubmit={handleSubmit}>
        <div className="field">
          <label>Target Role</label>
          <select value={role} onChange={(e) => setRole(e.target.value)}>
            {ROLES.map((r) => (
              <option key={r} value={r}>
                {r}
              </option>
            ))}
          </select>
        </div>

        <div className="field">
          <label>Resume (PDF)</label>
          <input
            type="file"
            accept=".pdf,.doc,.docx"
            onChange={(e) => setResumeFile(e.target.files[0] || null)}
          />
          {resumeFile && (
            <p style={{ color: "var(--muted)", fontSize: 13, marginTop: 4 }}>
              Selected: {resumeFile.name}
            </p>
          )}
        </div>

        <button type="submit" className="button primary">
          Continue to Interview
        </button>
      </form>
    </div>
  );
}
