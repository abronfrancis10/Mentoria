const BASE_URL = process.env.REACT_APP_API_BASE || "http://localhost:8000";

export async function ping() {
  const res = await fetch(`${BASE_URL}/ping`);
  return res.json();
}

export async function startInterview(payload) {
  const res = await fetch(`${BASE_URL}/api/interviews/start`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  return res.json();
}

export async function submitTextAnswer(interviewId, answer) {
  const res = await fetch(`${BASE_URL}/api/interviews/${interviewId}/answer`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ answer }),
  });
  return res.json();
}

export async function submitAudioAnswer(interviewId, audioBlob, snapshotBlob) {
  const form = new FormData();
  form.append("audio", audioBlob, "answer.webm");
  if (snapshotBlob) form.append("snapshot", snapshotBlob, "snapshot.png");

  const res = await fetch(
    `${BASE_URL}/api/interviews/${interviewId}/answer/audio`,
    { method: "POST", body: form }
  );
  return res.json();
}
