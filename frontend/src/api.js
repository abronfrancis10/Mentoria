const BASE_URL = process.env.REACT_APP_API_BASE || "http://localhost:8000";
const FACE_TIMEOUT_MS = 12000;
const VOICE_TIMEOUT_MS = 90000;

async function fetchWithTimeout(url, options = {}, timeoutMs = 15000) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  try {
    return await fetch(url, { ...options, signal: controller.signal });
  } finally {
    clearTimeout(timer);
  }
}

export async function ping() {
  const res = await fetch(`${BASE_URL}/`);
  return res.json();
}

export async function startInterview(
  role,
  resumeFile,
  userId = "anonymous",
  totalQuestions = 10,
  adaptiveContext = null
) {
  const form = new FormData();
  form.append("role", role);
  form.append("resume", resumeFile);
  form.append("user_id", userId || "anonymous");
  form.append("total_questions", String(totalQuestions || 10));
  if (adaptiveContext && typeof adaptiveContext === "object") {
    form.append("adaptive_context", JSON.stringify(adaptiveContext));
  }

  const res = await fetch(`${BASE_URL}/start-interview`, {
    method: "POST",
    body: form,
  });
  const data = await res.json();
  if (!res.ok) {
    throw new Error(String(data?.detail || data?.error || `Failed to start interview (${res.status})`));
  }
  return data;
}

export async function getNextQuestion(interviewId) {
  const res = await fetch(`${BASE_URL}/next-question/${interviewId}`);
  return res.json();
}

export async function submitTextAnswer(interviewId, payload) {
  const body = typeof payload === "string" ? { answer: payload } : payload;
  const res = await fetch(`${BASE_URL}/submit-answer/${interviewId}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  return res.json();
}

export async function analyzeFaceFrame(interviewId, imageBlob) {
  const form = new FormData();
  form.append("interview_id", interviewId);
  form.append("file", imageBlob, "frame.jpg");

  const res = await fetchWithTimeout(`${BASE_URL}/analyze-face-frame`, {
    method: "POST",
    body: form,
  }, FACE_TIMEOUT_MS);
  if (!res.ok) {
    throw new Error(`Face analysis failed (${res.status})`);
  }
  return res.json();
}

export async function getMonitorReport(interviewId) {
  const res = await fetch(`${BASE_URL}/monitor-report/${interviewId}`);
  return res.json();
}

export async function finalizeAnalyticsSession(interviewId, payload = {}) {
  const res = await fetch(`${BASE_URL}/analytics/session/finalize/${interviewId}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  return res.json();
}

export async function getAnalyticsSession(sessionId) {
  const res = await fetch(`${BASE_URL}/analytics/session/${sessionId}`);
  return res.json();
}

export async function getAnalyticsTrends(userId = "anonymous") {
  const res = await fetch(`${BASE_URL}/analytics/trends?user_id=${encodeURIComponent(userId || "anonymous")}`);
  return res.json();
}

export async function requestPeerReview(payload) {
  const res = await fetch(`${BASE_URL}/peer-review/request`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload || {}),
  });
  return res.json();
}

export async function submitPeerReview(payload) {
  const res = await fetch(`${BASE_URL}/peer-review/submit`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload || {}),
  });
  return res.json();
}

export async function getPeerReviewSession(sessionId) {
  const res = await fetch(`${BASE_URL}/peer-review/${encodeURIComponent(sessionId)}`);
  return res.json();
}

export async function submitAudioAnswer(interviewId, audioBlob, context = {}) {
  const form = new FormData();
  form.append("file", audioBlob, "answer.webm");
  form.append("transcript", String(context.fallbackTranscript || ""));

  let speechData = {};
  try {
    const speech = await fetch(`${BASE_URL}/analyze-voice-browser-speech`, {
      method: "POST",
      body: form,
    });
    speechData = await speech.json();
  } catch {
    speechData = {};
  }

  const transcript = (context.fallbackTranscript || speechData.transcript || "").trim();
  const fillerWordCount = Number.isFinite(Number(speechData.filler_word_count))
    ? Number(speechData.filler_word_count)
    : 0;
  const wordsPerMinute = Number.isFinite(Number(speechData.words_per_minute))
    ? Number(speechData.words_per_minute)
    : 0;
  const voiceScore = Number.isFinite(Number(speechData.voice_score))
    ? Number(speechData.voice_score)
    : 0;
  const speechRate = Number.isFinite(Number(speechData.speech_rate))
    ? Number(speechData.speech_rate)
    : wordsPerMinute;
  const pauseCount = Number.isFinite(Number(speechData.pause_count))
    ? Number(speechData.pause_count)
    : 0;
  const longPauseCount = Number.isFinite(Number(speechData.long_pause_count))
    ? Number(speechData.long_pause_count)
    : 0;
  const pauseFrequency = Number.isFinite(Number(speechData.pause_frequency))
    ? Number(speechData.pause_frequency)
    : 0;
  const toneVariationScore = Number.isFinite(Number(speechData.tone_variation_score))
    ? Number(speechData.tone_variation_score)
    : 0;
  const clarityScore = Number.isFinite(Number(speechData.clarity_score))
    ? Number(speechData.clarity_score)
    : 0;

  if (!transcript) {
    return {
      ...speechData,
      final_score: null,
      feedback: "No transcript detected from browser speech.",
    };
  }

  const scored = await submitTextAnswer(interviewId, {
    answer: transcript,
    question: context.question || "",
    role: context.role || "General",
    difficulty: context.difficulty || "medium",
    emotion_score: context.emotion_score,
    emotion_label: context.emotion_label,
    text_emotion_score: context.text_emotion_score,
    text_emotion_label: context.text_emotion_label,
    face_emotion_score: context.face_emotion_score ?? context.emotion_score,
    face_emotion_label: context.face_emotion_label ?? context.emotion_label,
    voice_score: voiceScore,
    filler_word_count: fillerWordCount,
    words_per_minute: wordsPerMinute,
    speech_rate: speechRate,
    pause_count: pauseCount,
    long_pause_count: longPauseCount,
    pause_frequency: pauseFrequency,
    tone_variation_score: toneVariationScore,
    clarity_score: clarityScore,
  });

  return {
    ...scored,
    transcript,
    filler_word_count: scored?.filler_word_count ?? fillerWordCount,
    words_per_minute: scored?.words_per_minute ?? wordsPerMinute,
    speech_rate: scored?.speech_rate ?? speechRate,
    pause_count: scored?.pause_count ?? pauseCount,
    long_pause_count: scored?.long_pause_count ?? longPauseCount,
    pause_frequency: scored?.pause_frequency ?? pauseFrequency,
    tone_variation_score: scored?.tone_variation_score ?? toneVariationScore,
    clarity_score: scored?.clarity_score ?? clarityScore,
    voice_score: scored?.voice_score ?? voiceScore,
  };
}

export async function analyzeVoiceWhisper(audioBlob) {
  const form = new FormData();
  form.append("file", audioBlob, "chunk.webm");
  const res = await fetchWithTimeout(`${BASE_URL}/analyze-voice-browser-speech`, {
    method: "POST",
    body: form,
  }, VOICE_TIMEOUT_MS);
  if (!res.ok) {
    throw new Error(`Speech endpoint failed (${res.status})`);
  }
  const data = await res.json();
  if (data?.error) {
    throw new Error(String(data.error));
  }
  return data;
}
