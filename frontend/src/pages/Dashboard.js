import React from "react";
import { Link } from "react-router-dom";

function renderTrend(values = []) {
  if (!values.length) return "-";
  return values.map((item) => Number(item.value ?? item.ordinal ?? 0).toFixed(1)).join(" -> ");
}

export default function Dashboard({ progress = [], trends = null }) {
  const totals = trends?.total_sessions ?? progress.length;

  return (
    <div>
      <h2>Dashboard</h2>

      {totals === 0 ? (
        <p>No sessions yet. Complete an interview to see your progress.</p>
      ) : (
        <>
          <p style={{ color: "var(--muted)" }}>
            Showing {totals} session{totals > 1 ? "s" : ""}.
          </p>

          {trends && (
            <div style={{ marginBottom: 14, padding: 10, border: "1px solid #e5e7eb", borderRadius: 8 }}>
              <p><strong>Average Score:</strong> {Number(trends.average_score ?? 0).toFixed(2)}</p>
              <p><strong>Improvement Delta:</strong> {Number(trends.improvement_delta ?? 0).toFixed(2)}</p>
              <p><strong>Emotion Avg:</strong> {Number(trends?.averages?.emotion_score ?? 0).toFixed(2)}</p>
              <p><strong>Attention Avg:</strong> {Number(trends?.averages?.attention_score ?? 0).toFixed(2)}</p>
              <p><strong>Voice Avg:</strong> {Number(trends?.averages?.voice_score ?? 0).toFixed(2)}</p>
              <p><strong>Linguistic Avg:</strong> {Number(trends?.averages?.linguistic_score ?? 0).toFixed(2)}</p>
            </div>
          )}

          {trends && (
            <div style={{ marginBottom: 16 }}>
              <h3>Trend Series</h3>
              <p><strong>Overall Score:</strong> {renderTrend(trends.overall_score_trend || [])}</p>
              <p><strong>Emotion:</strong> {renderTrend(trends.emotion_score_trend || [])}</p>
              <p><strong>Attention:</strong> {renderTrend(trends.attention_score_trend || [])}</p>
              <p><strong>Voice:</strong> {renderTrend(trends.voice_score_trend || [])}</p>
              <p><strong>Difficulty Progression:</strong> {renderTrend(trends.difficulty_progression_trend || [])}</p>
              <p><strong>Relevance:</strong> {renderTrend(trends?.linguistic_subscore_trends?.relevance_score || [])}</p>
              <p><strong>Structure:</strong> {renderTrend(trends?.linguistic_subscore_trends?.structure_score || [])}</p>
              <p><strong>Grammar:</strong> {renderTrend(trends?.linguistic_subscore_trends?.grammar_score || [])}</p>
              <p><strong>Keyword Match:</strong> {renderTrend(trends?.linguistic_subscore_trends?.keyword_match_score || [])}</p>
            </div>
          )}

          <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 14 }}>
            <thead>
              <tr>
                <th style={{ textAlign: "left", padding: 8 }}>Date</th>
                <th style={{ textAlign: "left", padding: 8 }}>Role</th>
                <th style={{ textAlign: "left", padding: 8 }}>Level</th>
                <th style={{ textAlign: "left", padding: 8 }}>Score</th>
                <th style={{ textAlign: "left", padding: 8 }}>Final Difficulty</th>
              </tr>
            </thead>
            <tbody>
              {progress.map((s, idx) => (
                <tr key={idx} style={{ borderTop: "1px solid #e5e7eb" }}>
                  <td style={{ padding: 8 }}>
                    {new Date(s.date || s.completed_at || s.timestamp || Date.now()).toLocaleString()}
                  </td>
                  <td style={{ padding: 8 }}>{s.role || "-"}</td>
                  <td style={{ padding: 8 }}>{s.level || "In Progress"}</td>
                  <td style={{ padding: 8 }}>
                    {Number(s.score ?? s.overall_score ?? 0).toFixed(2)}/10
                  </td>
                  <td style={{ padding: 8 }}>{s.final_difficulty_reached || "-"}</td>
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

