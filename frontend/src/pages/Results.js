import React from "react";
import { Link } from "react-router-dom";

export default function Results({ result }) {
  if (!result) {
    return (
      <div>
        <h2>Results</h2>
        <p>No interview results found. Please complete an interview first.</p>
        <Link to="/interview">Go to Interview</Link>
      </div>
    );
  }

  return (
    <div>
      <h2>Results</h2>
      <p>
        <strong>Current Level:</strong> {result.level}
      </p>
      <p>
        <strong>Score:</strong> {result.score}/10
      </p>

      <h3>Areas to Improve</h3>
      <ul>
        {result.improvements.map((item, i) => (
          <li key={i}>{item}</li>
        ))}
      </ul>

      <h3>Things to Avoid</h3>
      <ul>
        {result.avoid.map((item, i) => (
          <li key={i}>{item}</li>
        ))}
      </ul>

      <div style={{ marginTop: 16 }}>
        <Link to="/dashboard" className="button primary" style={{ padding: "8px 14px" }}>
          View Progress Dashboard
        </Link>
      </div>
    </div>
  );
}
