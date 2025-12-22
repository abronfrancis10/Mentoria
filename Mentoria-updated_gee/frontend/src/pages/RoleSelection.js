import React, { useState } from "react";
import { Link } from "react-router-dom";
import Navbar from "../components/Navbar"; // Include logo/navbar
import "./RoleSelection.css";

const ROLES = [
  "Software Engineer",
  "Data Analyst",
  "Frontend Developer",
  "Backend Developer",
  "Full Stack Developer",
  "Machine Learning Engineer",
  "AI/ML Researcher",
  "DevOps Engineer",
  "Product Manager",
  "UI/UX Designer",
  "Quality Assurance Engineer",
  "HR / Behavioral",
];

export default function RoleSelection({ onNext }) {
  const [role, setRole] = useState(ROLES[0]);
  const [resumeFile, setResumeFile] = useState(null);
  const [error, setError] = useState("");

  function handleSubmit(e) {
    e.preventDefault();

    // Resume validation
    if (!resumeFile) {
      setError("Please upload your resume to continue.");
      return;
    }

    // Proceed if valid
    setError("");
    onNext({
      role,
      resumeName: resumeFile.name,
    });
  }

  return (
    <>
      <Navbar />

      <div className="role-wrapper">
        <div className="role-card">
          <h2>Select Role & Upload Resume</h2>
          <p className="home-caption">
            Choose your target role and upload your resume to start your AI-powered interview experience.
          </p>

          <form onSubmit={handleSubmit} className="auth-form">
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
              <label>Resume (PDF/DOC)</label>
              <input
                type="file"
                accept=".pdf,.doc,.docx"
                onChange={(e) => setResumeFile(e.target.files[0] || null)}
              />
              {resumeFile && (
                <p className="role-caption">Selected: {resumeFile.name}</p>
              )}
            </div>

            {error && <p className="error-text">{error}</p>}

            <button type="submit" className="button primary">
              Continue to Interview
            </button>
          </form>

          <p className="signup-text" style={{ marginTop: "1rem", fontSize: 14 }}>
            Want to go back? <Link to="/">Home</Link>
          </p>
        </div>
      </div>
    </>
  );
}
