// src/api.js

const BASE_URL = "http://localhost:8000";

/* -------------------------
   Health check
------------------------- */
export const ping = async () => {
  const res = await fetch(`${BASE_URL}/`);
  return res.json();
};

/* -------------------------
   Start Interview (ROLE + RESUME)
------------------------- */
export const startInterview = async (role, resumeFile) => {
  const form = new FormData();
  form.append("role", role);

  if (resumeFile) {
    form.append("resume", resumeFile);
  }

  const res = await fetch(`${BASE_URL}/start-interview`, {
    method: "POST",
    body: form,
  });

  return res.json();
};

/* -------------------------
   Get Next Question
------------------------- */
export const getNextQuestion = async (interviewId) => {
  const res = await fetch(`${BASE_URL}/next-question/${interviewId}`);
  return res.json();
};

/* -------------------------
   Submit TEXT Answer
------------------------- */
export const submitTextAnswer = async (interviewId, answer) => {
  const res = await fetch(`${BASE_URL}/submit-answer/${interviewId}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ answer }),
  });

  return res.json();
};

/* -------------------------
   Submit AUDIO Answer (Whisper)
------------------------- */
export const submitAudioAnswer = async (interviewId, audioBlob) => {
  const form = new FormData();
  form.append("file", audioBlob, "answer.webm");

  const res = await fetch(
    `${BASE_URL}/analyze-voice-whisper/${interviewId}`,
    {
      method: "POST",
      body: form,
    }
  );

  return res.json();
};
