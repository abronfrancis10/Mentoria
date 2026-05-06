import React, { useEffect, useState } from "react";
import { Routes, Route, useNavigate } from "react-router-dom";
import { onAuthStateChanged } from "firebase/auth";

import { finalizeAnalyticsSession, getAnalyticsTrends } from "./api";
import { getUserAdaptiveProfile, persistInterviewSession } from "./adaptiveLearning";
import { auth } from "./firebase";
import Landing from "./pages/Landing";
import Home from "./pages/Home";
import Signup from "./pages/Signup";
import RoleSelection from "./pages/RoleSelection";
import Interview from "./pages/Interview";
import Results from "./pages/Results";
import Dashboard from "./pages/Dashboard";

export default function App() {
  const navigate = useNavigate();

  const [user, setUser] = useState(null);
  const [roleInfo, setRoleInfo] = useState(null);
  const [lastResult, setLastResult] = useState(null);
  const [progress, setProgress] = useState([]);
  const [trendData, setTrendData] = useState(null);
  const [adaptiveProfile, setAdaptiveProfile] = useState(null);

  function buildSessionKey(session) {
    const role = String(session?.role || "").trim().toLowerCase();
    const score = Number(session?.overall_score ?? session?.score ?? 0).toFixed(2);
    const summary = String(session?.feedbackSummary || "").trim().toLowerCase();
    const transcript = String(session?.transcript || "")
      .replace(/\s+/g, " ")
      .trim()
      .toLowerCase()
      .slice(0, 300);
    const qnaCount = Array.isArray(session?.reviewedQnA) ? session.reviewedQnA.length : 0;
    return `${role}|${score}|${qnaCount}|${summary}|${transcript}`;
  }

  async function refreshTrends(userId) {
    try {
      const trends = await getAnalyticsTrends(userId || "anonymous");
      setTrendData(trends);
      const sessions = Array.isArray(trends?.sessions) ? trends.sessions : [];
      setProgress(
        sessions.map((session) => ({
          ...session,
          date: session.completed_at || session.timestamp || new Date().toISOString(),
          score: Number(session.overall_score ?? 0),
          level: Number(session.overall_score ?? 0) >= 8
            ? "Advanced"
            : Number(session.overall_score ?? 0) >= 6
              ? "Intermediate"
              : "Beginner",
        }))
      );
    } catch {
      // keep local fallback progress
    }
  }

  useEffect(() => {
    const unsubscribe = onAuthStateChanged(auth, async (firebaseUser) => {
      if (!firebaseUser) {
        setUser(null);
        setAdaptiveProfile(null);
        return;
      }

      const normalizedUser = {
        uid: firebaseUser.uid,
        email: firebaseUser.email || "",
        name: firebaseUser.displayName || "",
      };
      setUser(normalizedUser);
      const stableUserId = normalizedUser.uid || normalizedUser.email || "anonymous";
      try {
        const profile = await getUserAdaptiveProfile(stableUserId);
        setAdaptiveProfile(profile);
        await refreshTrends(stableUserId);
      } catch {
        setAdaptiveProfile(null);
      }
    });
    return () => unsubscribe();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  function handleLogin(userData) {
    setUser(userData);
    const stableUserId = userData?.uid || userData?.email || "anonymous";
    getUserAdaptiveProfile(stableUserId)
      .then((profile) => setAdaptiveProfile(profile))
      .catch(() => setAdaptiveProfile(null));
    navigate("/role");
  }

  function handleRoleSelected(info) {
    const inferredUserId = user?.uid || user?.email || "anonymous";
    const adaptiveContext = {
      previous_overall_interview_score: Number(adaptiveProfile?.previousOverallInterviewScore ?? 0),
      average_overall_interview_score: Number(adaptiveProfile?.averageOverallInterviewScore ?? 0),
      latest_level: String(adaptiveProfile?.latestLevel || "Beginner"),
      recommended_level: String(adaptiveProfile?.recommendedLevel || "Beginner"),
      score_trend: Array.isArray(adaptiveProfile?.scoreTrend) ? adaptiveProfile.scoreTrend : [],
      weak_areas: Array.isArray(adaptiveProfile?.weakAreas) ? adaptiveProfile.weakAreas : [],
      strengths: Array.isArray(adaptiveProfile?.strengths) ? adaptiveProfile.strengths : [],
      recent_roles: Array.isArray(adaptiveProfile?.recentRoles) ? adaptiveProfile.recentRoles : [],
      sessions_count: Number(adaptiveProfile?.sessionsCount ?? 0),
    };
    setRoleInfo({
      ...info,
      userId: info?.userId || inferredUserId,
      adaptiveContext,
    });
    navigate("/interview");
  }

  async function handleInterviewComplete(result) {
    const userId = roleInfo?.userId || user?.uid || user?.email || "anonymous";
    let finalizedSession = null;
    if (result?.interview_id) {
      try {
        const finalize = await finalizeAnalyticsSession(result.interview_id, {
          user_id: userId,
          role: roleInfo?.role || "",
        });
        finalizedSession = finalize?.session || null;
      } catch {
        finalizedSession = null;
      }
    }

    const session = {
      ...result,
      role: roleInfo?.role,
      userId,
      date: new Date().toISOString(),
      analyticsSessionId: finalizedSession?.session_id || result?.analyticsSessionId || "",
      persistedSession: finalizedSession || null,
    };
    const sessionKey = buildSessionKey(session);
    const dedupedSession = { ...session, sessionKey };

    setLastResult(dedupedSession);
    setProgress((prev) => {
      if (prev.some((item) => item?.sessionKey === sessionKey)) {
        return prev;
      }
      return [...prev, dedupedSession];
    });

    try {
      const nextProfile = await persistInterviewSession(userId, dedupedSession);
      if (nextProfile) {
        setAdaptiveProfile(nextProfile);
      }
    } catch {
      // Firestore write failure should not block interview completion UX.
    }

    await refreshTrends(userId);
    navigate("/results");
  }

  return (
    <Routes>
      <Route path="/" element={<Landing />} />
      <Route
        path="*"
        element={(
          <div className="container">
            <div className="card">
              <div
                style={{
                  display: "flex",
                  justifyContent: "space-between",
                  marginBottom: 16,
                }}
              >
                <div>
                  <h1 style={{ marginBottom: 4 }}>Mentoria</h1>
                  <p style={{ margin: 0, color: "var(--muted)" }}>
                    AI Interview Trainer
                  </p>
                </div>
                <div style={{ textAlign: "right", fontSize: 14 }}>
                  {user ? (
                    <>
                      <div>Hi, {user.name || user.email || "User"}</div>
                      <div style={{ color: "var(--muted)" }}>
                        {roleInfo ? `Role: ${roleInfo.role}` : "No role selected"}
                      </div>
                    </>
                  ) : (
                    <div style={{ color: "var(--muted)" }}>
                      Not logged in
                    </div>
                  )}
                </div>
              </div>

              <Routes>
                <Route path="/login" element={<Home onLogin={handleLogin} />} />
                <Route path="/signup" element={<Signup />} />
                <Route path="/role" element={<RoleSelection onNext={handleRoleSelected} />} />
                <Route
                  path="/interview"
                  element={<Interview roleInfo={roleInfo} onComplete={handleInterviewComplete} />}
                />
                <Route
                  path="/results"
                  element={(
                    <Results
                      result={lastResult}
                      currentUserId={roleInfo?.userId || user?.uid || user?.email || "anonymous"}
                    />
                  )}
                />
                <Route
                  path="/dashboard"
                  element={<Dashboard progress={progress} trends={trendData} />}
                />
              </Routes>
            </div>
          </div>
        )}
      />
    </Routes>
  );
}
