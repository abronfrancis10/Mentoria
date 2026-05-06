import {
  addDoc,
  collection,
  doc,
  getDoc,
  getDocs,
  limit,
  orderBy,
  query,
  serverTimestamp,
  setDoc,
} from "firebase/firestore";

import { db } from "./firebase";

const DEFAULT_PROFILE = {
  previousOverallInterviewScore: 0,
  averageOverallInterviewScore: 0,
  latestLevel: "Beginner",
  recommendedLevel: "Beginner",
  scoreTrend: [],
  weakAreas: [],
  strengths: [],
  recentRoles: [],
  sessionsCount: 0,
};

function normalizeUserId(userId) {
  const raw = String(userId || "").trim();
  if (!raw) return "anonymous";
  return raw.replace(/\//g, "_");
}

function toNumber(value, fallback = 0) {
  const num = Number(value);
  return Number.isFinite(num) ? num : fallback;
}

export function scoreToLevel(score) {
  const normalized = toNumber(score, 0);
  if (normalized >= 8) return "Advanced";
  if (normalized >= 6) return "Intermediate";
  return "Beginner";
}

function levelToDifficulty(level) {
  const normalized = String(level || "").toLowerCase();
  if (normalized === "advanced") return "hard";
  if (normalized === "intermediate") return "medium";
  return "easy";
}

function topKeys(counter, limitCount = 5) {
  return Object.entries(counter)
    .sort((a, b) => b[1] - a[1])
    .slice(0, limitCount)
    .map(([key]) => key);
}

function buildProfileFromSessions(sessions = [], persistedProfile = {}) {
  if (!Array.isArray(sessions) || sessions.length === 0) {
    const fallbackScore = toNumber(persistedProfile.previousOverallInterviewScore, 0);
    const fallbackLevel = persistedProfile.latestLevel || scoreToLevel(fallbackScore);
    const recommendedLevel = persistedProfile.recommendedLevel || scoreToLevel(fallbackScore);
    return {
      ...DEFAULT_PROFILE,
      ...persistedProfile,
      previousOverallInterviewScore: fallbackScore,
      averageOverallInterviewScore: toNumber(persistedProfile.averageOverallInterviewScore, fallbackScore),
      latestLevel: fallbackLevel,
      recommendedLevel,
      recommendedDifficulty: levelToDifficulty(recommendedLevel),
    };
  }

  const scores = sessions.map((session) => toNumber(session.overallInterviewScore, 0));
  const lastScore = scores[0] ?? 0;
  const avgScore = scores.length > 0
    ? Number((scores.reduce((sum, item) => sum + item, 0) / scores.length).toFixed(2))
    : 0;
  const trend = scores.slice(0, 5);
  const latestLevel = sessions[0]?.level || scoreToLevel(lastScore);

  const weakCounter = {};
  const strengthCounter = {};
  const rolesCounter = {};

  sessions.forEach((session) => {
    (session.improvements || []).forEach((item) => {
      const key = String(item || "").trim();
      if (!key) return;
      weakCounter[key] = (weakCounter[key] || 0) + 1;
    });
    (session.strengths || []).forEach((item) => {
      const key = String(item || "").trim();
      if (!key) return;
      strengthCounter[key] = (strengthCounter[key] || 0) + 1;
    });
    const roleKey = String(session.role || "").trim();
    if (roleKey) {
      rolesCounter[roleKey] = (rolesCounter[roleKey] || 0) + 1;
    }
  });

  const recommendedLevel = scoreToLevel(avgScore > 0 ? avgScore : lastScore);

  return {
    previousOverallInterviewScore: Number(lastScore.toFixed(2)),
    averageOverallInterviewScore: avgScore,
    latestLevel,
    recommendedLevel,
    recommendedDifficulty: levelToDifficulty(recommendedLevel),
    scoreTrend: trend.map((item) => Number(item.toFixed(2))),
    weakAreas: topKeys(weakCounter, 5),
    strengths: topKeys(strengthCounter, 5),
    recentRoles: topKeys(rolesCounter, 3),
    sessionsCount: sessions.length,
  };
}

function normalizeSessionPayload(session = {}) {
  const persistedSession = session.persistedSession || {};
  const overallInterviewScore = toNumber(
    session.overallInterviewScore
      ?? session.score
      ?? persistedSession.overall_interview_score
      ?? persistedSession.overall_score
      ?? 0,
    0
  );

  const level = session.level || scoreToLevel(overallInterviewScore);

  return {
    role: String(session.role || persistedSession.role || "").trim(),
    overallInterviewScore: Number(overallInterviewScore.toFixed(2)),
    level,
    strengths: Array.isArray(session.strengths) ? session.strengths.slice(0, 10) : [],
    improvements: Array.isArray(session.improvements) ? session.improvements.slice(0, 10) : [],
    score: toNumber(session.score ?? persistedSession.overall_score ?? overallInterviewScore, 0),
    difficultyHistory: Array.isArray(session.difficultyHistory) ? session.difficultyHistory : [],
    questionLevelHistory: Array.isArray(session.questionLevelHistory) ? session.questionLevelHistory : [],
    feedbackSummary: String(session.feedbackSummary || "").trim(),
    completedAtIso: new Date().toISOString(),
    analyticsSessionId: String(
      session.analyticsSessionId
        || persistedSession.session_id
        || ""
    ).trim(),
  };
}

export async function getUserAdaptiveProfile(userId) {
  const normalizedUserId = normalizeUserId(userId);
  if (normalizedUserId === "anonymous") {
    return {
      userId: normalizedUserId,
      ...DEFAULT_PROFILE,
      recommendedDifficulty: "easy",
    };
  }

  const userDocRef = doc(db, "users", normalizedUserId);
  const sessionsRef = collection(db, "users", normalizedUserId, "interview_sessions");

  const [userDocSnap, sessionsSnap] = await Promise.all([
    getDoc(userDocRef),
    getDocs(query(sessionsRef, orderBy("completedAt", "desc"), limit(20))),
  ]);

  const persistedProfile = userDocSnap.exists()
    ? (userDocSnap.data()?.adaptiveProfile || {})
    : {};
  const sessions = sessionsSnap.docs.map((item) => item.data() || {});
  const profile = buildProfileFromSessions(sessions, persistedProfile);

  return {
    userId: normalizedUserId,
    ...profile,
  };
}

export async function persistInterviewSession(userId, sessionPayload) {
  const normalizedUserId = normalizeUserId(userId);
  if (normalizedUserId === "anonymous" || !sessionPayload) {
    return null;
  }

  const session = normalizeSessionPayload(sessionPayload);
  const sessionsRef = collection(db, "users", normalizedUserId, "interview_sessions");

  await addDoc(sessionsRef, {
    ...session,
    createdAt: serverTimestamp(),
    completedAt: serverTimestamp(),
  });

  const latestSessionsSnap = await getDocs(
    query(sessionsRef, orderBy("completedAt", "desc"), limit(20))
  );
  const latestSessions = latestSessionsSnap.docs.map((item) => item.data() || {});
  const adaptiveProfile = buildProfileFromSessions(latestSessions);

  await setDoc(
    doc(db, "users", normalizedUserId),
    {
      adaptiveProfile,
      updatedAt: serverTimestamp(),
    },
    { merge: true }
  );

  return adaptiveProfile;
}

