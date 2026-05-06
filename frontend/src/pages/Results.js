import React, { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";

import { getPeerReviewSession, requestPeerReview, submitPeerReview } from "../api";

export default function Results({ result, currentUserId = "anonymous" }) {
  const [peerReviewNotes, setPeerReviewNotes] = useState("");
  const [peerReviewRequested, setPeerReviewRequested] = useState(false);
  const [peerReviewError, setPeerReviewError] = useState("");
  const [reviewerName, setReviewerName] = useState("");
  const [reviewerComments, setReviewerComments] = useState("");
  const [overallRating, setOverallRating] = useState(4);
  const [communicationRating, setCommunicationRating] = useState(4);
  const [technicalRating, setTechnicalRating] = useState(4);
  const [peerReviewData, setPeerReviewData] = useState(null);
  const [peerReviewLoading, setPeerReviewLoading] = useState(false);

  const sessionId = useMemo(
    () => result?.analyticsSessionId || result?.persistedSession?.session_id || "",
    [result]
  );
  const sessionOwnerId = useMemo(
    () => result?.persistedSession?.user_id || result?.userId || currentUserId || "anonymous",
    [result, currentUserId]
  );

  useEffect(() => {
    if (!sessionId) return;
    setPeerReviewLoading(true);
    getPeerReviewSession(sessionId)
      .then((data) => setPeerReviewData(data))
      .catch(() => setPeerReviewData(null))
      .finally(() => setPeerReviewLoading(false));
  }, [sessionId]);

  if (!result) {
    return (
      <div>
        <h2>Results</h2>
        <p>No interview results found. Please complete an interview first.</p>
        <Link to="/interview">Go to Interview</Link>
      </div>
    );
  }

  const strengths = result.strengths || [];
  const improvements = result.improvements || [];
  const avoid = result.avoid || [];
  const level = result.level || "In Progress";
  const overallInterviewScore = Number(
    result.overallInterviewScore
      ?? result.persistedSession?.overall_interview_score
      ?? result.score
      ?? result.persistedSession?.overall_score
      ?? 0
  );
  const emotionScore = Number(result.emotionScore ?? result.persistedSession?.emotion_score ?? 0);
  const textEmotionScore = Number(result.textEmotionScore ?? result.persistedSession?.text_emotion_score ?? 0);
  const faceEmotionScore = Number(result.faceEmotionScore ?? result.persistedSession?.face_emotion_score ?? 0);
  const voiceScore = Number(result.voiceScore ?? result.persistedSession?.voice_score ?? 0);
  const answerQualityScore = Number(result.answerQualityScore ?? result.persistedSession?.answer_quality_score ?? 0);
  const optimalAlignmentScore = Number(
    result.optimalAlignmentScore ?? result.persistedSession?.optimal_alignment_score ?? 0
  );
  const monitorFinalAttentionScore = Number(
    result.monitorFinalAttentionScore
      ?? result.persistedSession?.monitor_report?.final_attention_score
      ?? 0
  );
  const monitorEmotionScorePercent = Number(
    result.monitorEmotionScorePercent
      ?? result.persistedSession?.monitor_report?.emotion_score_percent
      ?? 0
  );
  const issueCounts = result.issueCounts
    || result.persistedSession?.monitor_report?.issue_counts
    || {};
  const attentionFeedback = result.attentionFeedback
    || result.persistedSession?.monitor_report?.attention_feedback
    || null;
  const emotionFeedback = result.emotionFeedback
    || result.persistedSession?.monitor_report?.emotion_feedback
    || null;
  const reviewedQnA = result.reviewedQnA || [];
  const suggestedAnswers = result.suggestedAnswers || [];

  const summary = result.feedbackSummary
    || result.feedback
    || "Your interview has been analyzed. Keep practicing role-specific examples with clear structure.";

  async function handlePeerReviewRequest() {
    setPeerReviewError("");
    if (!sessionId) {
      setPeerReviewError("Analytics session is not available yet. Complete interview finalization first.");
      return;
    }
    try {
      const response = await requestPeerReview({
        session_id: sessionId,
        requester_id: currentUserId || "anonymous",
        focus_areas: peerReviewNotes || "",
      });
      if (response?.detail) {
        setPeerReviewError(String(response.detail));
        return;
      }
      setPeerReviewRequested(true);
      const latest = await getPeerReviewSession(sessionId);
      setPeerReviewData(latest);
    } catch {
      setPeerReviewError("Failed to request peer review.");
    }
  }

  async function handlePeerReviewSubmit() {
    setPeerReviewError("");
    if (!sessionId) {
      setPeerReviewError("Session id is missing.");
      return;
    }
    try {
      const response = await submitPeerReview({
        session_id: sessionId,
        reviewer_id: currentUserId || "anonymous",
        reviewer_name: reviewerName,
        session_owner_id: sessionOwnerId,
        overall_rating: Number(overallRating),
        communication_rating: Number(communicationRating),
        technical_rating: Number(technicalRating),
        comments: reviewerComments,
      });
      if (response?.detail) {
        setPeerReviewError(String(response.detail));
        return;
      }
      const latest = await getPeerReviewSession(sessionId);
      setPeerReviewData(latest);
      setReviewerComments("");
    } catch {
      setPeerReviewError("Failed to submit peer review.");
    }
  }

  return (
    <div>
      <h2>Results</h2>
      <p style={{ color: "var(--muted)" }}>
        <strong>Role:</strong> {result.role || "Not specified"}
      </p>
      <p><strong>Current Level:</strong> {level}</p>
      <p><strong>Overall Interview Score:</strong> {overallInterviewScore.toFixed(2)}/10</p>
      <p><strong>Emotion Score:</strong> {emotionScore > 0 ? `${emotionScore.toFixed(2)}/10` : "-"}</p>
      <p><strong>Text Emotion Score:</strong> {textEmotionScore > 0 ? `${textEmotionScore.toFixed(2)}/10` : "-"}</p>
      <p><strong>Face Emotion Score:</strong> {faceEmotionScore > 0 ? `${faceEmotionScore.toFixed(2)}/10` : "-"}</p>
      <p><strong>Voice Analysis Score:</strong> {voiceScore > 0 ? `${voiceScore.toFixed(2)}/10` : "-"}</p>
      <p><strong>Answer Quality Score:</strong> {answerQualityScore > 0 ? `${answerQualityScore.toFixed(2)}/10` : "-"}</p>
      <p><strong>Optimal Alignment Score:</strong> {optimalAlignmentScore > 0 ? `${optimalAlignmentScore.toFixed(2)}/10` : "-"}</p>

      <h3>Overall LLM Summary</h3>
      <p>{summary}</p>

      {strengths.length > 0 && (
        <>
          <h3>What Went Well</h3>
          <ul>
            {strengths.map((item, i) => (<li key={i}>{item}</li>))}
          </ul>
        </>
      )}

      <h3>Areas to Improve</h3>
      {improvements.length > 0 ? (
        <ul>{improvements.map((item, i) => (<li key={i}>{item}</li>))}</ul>
      ) : (
        <p style={{ color: "var(--muted)" }}>
          No specific improvement points returned. Continue practicing concise, structured answers.
        </p>
      )}

      <h3>Things to Avoid</h3>
      {avoid.length > 0 ? (
        <ul>{avoid.map((item, i) => (<li key={i}>{item}</li>))}</ul>
      ) : (
        <p style={{ color: "var(--muted)" }}>Avoid vague answers and unsupported claims without examples.</p>
      )}

      {suggestedAnswers.length > 0 && (
        <>
          <h3>LLM Suggested Better Answers</h3>
          <ul>{suggestedAnswers.map((item, i) => (<li key={i}>{item}</li>))}</ul>
        </>
      )}

      {reviewedQnA.length > 0 && (
        <>
          <h3>Reviewed Question Answers</h3>
          {reviewedQnA.map((entry, idx) => (
            <div key={idx} style={{ marginBottom: 14, padding: 10, border: "1px solid #e5e7eb", borderRadius: 8 }}>
              <p><strong>Q:</strong> {entry.question}</p>
              <p><strong>Your Answer:</strong> {entry.answer}</p>
              {entry.optimal_answer && <p><strong>Optimal Answer:</strong> {entry.optimal_answer}</p>}
              <p style={{ color: "var(--muted)" }}>
                Final {Number(entry.final_score ?? 0).toFixed(2)}/10 | LLM {Number(entry.llm_score ?? 0).toFixed(2)}/10
                {" | "}Emotion {Number(entry.emotion_score ?? 0).toFixed(1)}/10 | Voice {Number(entry.voice_score ?? 0).toFixed(1)}/10
                {" | "}Alignment {Number(entry.optimal_alignment_score ?? 0).toFixed(1)}/10
              </p>
              {entry.optimal_alignment_feedback && (
                <p style={{ color: "var(--muted)" }}>
                  <strong>Alignment Feedback:</strong> {entry.optimal_alignment_feedback}
                </p>
              )}
              {Array.isArray(entry.optimal_mismatch_points) && entry.optimal_mismatch_points.length > 0 && (
                <ul>
                  {entry.optimal_mismatch_points.map((item, i) => (
                    <li key={`mismatch-${idx}-${i}`}>{item}</li>
                  ))}
                </ul>
              )}
              {entry.overall_feedback && <p style={{ color: "var(--muted)" }}>Feedback: {entry.overall_feedback}</p>}
              {entry.suggested_answer && <p><strong>Suggested Better Answer:</strong> {entry.suggested_answer}</p>}
            </div>
          ))}
        </>
      )}

      {attentionFeedback && (
        <>
          <h3>Attention Analysis</h3>
          <p><strong>Final Attention Score:</strong> {monitorFinalAttentionScore}/100</p>
          <p>{attentionFeedback.headline}</p>
          {Array.isArray(attentionFeedback.details) && attentionFeedback.details.length > 0 && (
            <ul>{attentionFeedback.details.map((item, i) => (<li key={`attention-${i}`}>{item}</li>))}</ul>
          )}
          <p style={{ color: "var(--muted)" }}>
            Slouch: {Number(issueCounts.slouch_count ?? 0)}
            {" | "}Tilt: {Number(issueCounts.tilt_count ?? 0)}
            {" | "}Multiple Face: {Number(issueCounts.multi_face_count ?? 0)}
            {" | "}Face Not Clear: {Number(issueCounts.face_not_clear_count ?? 0)}
          </p>
        </>
      )}

      {emotionFeedback && (
        <>
          <h3>Emotion Analysis</h3>
          <p><strong>Positive Emotion Score:</strong> {monitorEmotionScorePercent}%</p>
          {emotionFeedback.distribution && Object.keys(emotionFeedback.distribution).length > 0 && (
            <ul>
              {Object.entries(emotionFeedback.distribution).map(([emotion, value]) => (
                <li key={`emotion-${emotion}`}>{emotion}: {Number(value).toFixed(1)}%</li>
              ))}
            </ul>
          )}
          <p>{emotionFeedback.headline}</p>
        </>
      )}

      <h3>Peer Review (Human Feedback)</h3>
      <p style={{ color: "var(--muted)" }}>
        Request and submit peer review using validated ratings (1-5) and detailed comments.
      </p>

      <textarea
        placeholder="Focus areas for peer review request"
        value={peerReviewNotes}
        onChange={(e) => setPeerReviewNotes(e.target.value)}
        rows={3}
      />
      <div style={{ marginTop: 10 }}>
        <button className="button primary" onClick={handlePeerReviewRequest}>Request Peer Review</button>
      </div>
      {peerReviewRequested && (
        <p style={{ marginTop: 10, color: "#065f46" }}>
          Peer review requested. {peerReviewNotes ? "Your notes were included." : "Add notes above for context."}
        </p>
      )}

      <div style={{ marginTop: 14, padding: 10, border: "1px solid #e5e7eb", borderRadius: 8 }}>
        <p><strong>Submit a Peer Review</strong></p>
        <input
          placeholder="Reviewer name"
          value={reviewerName}
          onChange={(e) => setReviewerName(e.target.value)}
        />
        <textarea
          placeholder="Comments (minimum 20 characters)"
          value={reviewerComments}
          onChange={(e) => setReviewerComments(e.target.value)}
          rows={3}
        />
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 8 }}>
          <label>
            Overall
            <input type="number" min="1" max="5" value={overallRating} onChange={(e) => setOverallRating(e.target.value)} />
          </label>
          <label>
            Communication
            <input type="number" min="1" max="5" value={communicationRating} onChange={(e) => setCommunicationRating(e.target.value)} />
          </label>
          <label>
            Technical
            <input type="number" min="1" max="5" value={technicalRating} onChange={(e) => setTechnicalRating(e.target.value)} />
          </label>
        </div>
        <button className="button primary" style={{ marginTop: 8 }} onClick={handlePeerReviewSubmit}>
          Submit Review
        </button>
      </div>

      {peerReviewError && <p style={{ color: "#b91c1c" }}>{peerReviewError}</p>}

      {peerReviewLoading && <p style={{ color: "var(--muted)" }}>Loading peer review data...</p>}
      {peerReviewData && (
        <div style={{ marginTop: 12 }}>
          <p><strong>Peer Review Count:</strong> {Number(peerReviewData.review_count ?? 0)}</p>
          <p>
            <strong>Averages:</strong> Overall {Number(peerReviewData?.averages?.overall_rating ?? 0).toFixed(2)}
            {" | "}Communication {Number(peerReviewData?.averages?.communication_rating ?? 0).toFixed(2)}
            {" | "}Technical {Number(peerReviewData?.averages?.technical_rating ?? 0).toFixed(2)}
          </p>
          {Array.isArray(peerReviewData.reviews) && peerReviewData.reviews.length > 0 && (
            <ul>
              {peerReviewData.reviews.map((r) => (
                <li key={r.review_id}>
                  {r.reviewer_name}: {r.comments} (Overall {r.overall_rating}/5)
                </li>
              ))}
            </ul>
          )}
        </div>
      )}

      <div style={{ marginTop: 16 }}>
        <Link to="/dashboard" className="button primary" style={{ padding: "8px 14px" }}>
          View Progress Dashboard
        </Link>
      </div>
    </div>
  );
}
