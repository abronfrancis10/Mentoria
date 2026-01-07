import React, { useState, useRef, useEffect } from "react";
import { ping, startInterview, submitTextAnswer, submitAudioAnswer } from "./api";

export default function App() {
  const [status, setStatus] = useState("checking backend...");
  const [interviewId, setInterviewId] = useState(null);
  const [question, setQuestion] = useState("Click Start Interview to begin.");
  const [answerText, setAnswerText] = useState("");
  const [transcript, setTranscript] = useState("");
  const [score, setScore] = useState(null);
  const [message, setMessage] = useState("");
  const videoRef = useRef(null);
  const canvasRef = useRef(null);
  const mediaRecorderRef = useRef(null);
  const chunksRef = useRef([]);
  const [isRecording, setIsRecording] = useState(false);
  const [mediaStream, setMediaStream] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    ping()
      .then(() => setStatus("backend available"))
      .catch(() => setStatus("no backend (ok for now)"));
  }, []);

  async function beginInterview() {
    try {
      setMessage("Starting interview...");
      const res = await startInterview({ role: "frontend", type: "hr" });
      setInterviewId(res.interview_id || "local-test");
      setQuestion(res.first_question || "Tell me about yourself.");
      setMessage("");
    } catch (err) {
      console.error(err);
      setMessage("Failed to start interview (backend error).");
    }
  }

  async function sendTextAnswer() {
    if (!interviewId) { setMessage("Please start an interview first."); return; }
    try {
      setMessage("Submitting text answer...");
      const res = await submitTextAnswer(interviewId, answerText);
      setTranscript(res.transcript || answerText);
      setScore(res.score ?? 0);
      setQuestion(res.next_question || "");
      setMessage("");
    } catch (err) {
      console.error(err);
      setMessage("Failed to submit text answer.");
    }
  }

  async function initMedia() {
    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
      throw new Error("Media devices API not supported in this browser.");
    }
    if (mediaStream) return mediaStream;
    const s = await navigator.mediaDevices.getUserMedia({ audio: true, video: true });
    setMediaStream(s);
    if (videoRef.current) videoRef.current.srcObject = s;
    return s;
  }

  async function startMediaRecorder() {
    if (isRecording) return;
    try {
      setError(null);
      await initMedia();
      if (typeof MediaRecorder === "undefined") {
        throw new Error("MediaRecorder is not supported in this browser.");
      }
      chunksRef.current = [];
      const recorder = new MediaRecorder(mediaStream || videoRef.current?.srcObject);
      mediaRecorderRef.current = recorder;
      recorder.ondataavailable = (e) => { if (e.data && e.data.size > 0) chunksRef.current.push(e.data); };
      recorder.onstop = async () => {
        try {
          const audioBlob = new Blob(chunksRef.current, { type: "audio/webm" });
          chunksRef.current = [];
          let snapshotBlob = null;
          if (canvasRef.current && videoRef.current) {
            const videoEl = videoRef.current;
            const canvas = canvasRef.current;
            const w = videoEl.videoWidth || 320;
            const h = videoEl.videoHeight || 240;
            canvas.width = w; canvas.height = h;
            const ctx = canvas.getContext("2d");
            try {
              ctx.drawImage(videoEl, 0, 0, w, h);
              const dataUrl = canvas.toDataURL("image/png");
              const response = await fetch(dataUrl);
              snapshotBlob = await response.blob();
            } catch (e) { console.warn("Snapshot failed", e); }
          }
          setMessage("Uploading audio for analysis...");
          const res = await submitAudioAnswer(interviewId || "local-test", audioBlob, snapshotBlob);
          setTranscript(res.transcript || "No transcript returned.");
          setScore(res.score ?? 0);
          setQuestion(res.next_question || "");
          setMessage("");
        } catch (e) {
          console.error("Error handling recorder stop:", e);
          setMessage("Failed processing recording.");
        }
      };
      recorder.start();
      setIsRecording(true);
      setMessage("Recording...");
    } catch (e) {
      console.error(e);
      setError(e.message || "Failed to start media.");
      setMessage("");
    }
  }

  function stopMediaRecorder() {
    if (mediaRecorderRef.current && mediaRecorderRef.current.state !== "inactive") {
      try { mediaRecorderRef.current.stop(); } catch (e) { console.warn("Error stopping recorder:", e); }
    }
    setIsRecording(false);
  }

  useEffect(() => {
    return () => { if (mediaStream) mediaStream.getTracks().forEach(t => t.stop()); };
  }, [mediaStream]);

  return (
    <div className="container">
      <div className="card">
        <h1>Mentoria — Interview Trainer</h1>
        <p style={{ color: "#374151" }}>Backend: <strong>{status}</strong></p>

        <div style={{ marginTop: 12 }}>
          <button className="button primary" onClick={beginInterview}>Start Interview</button>
          <span style={{ marginLeft: 12, color: "var(--muted)" }}>{message}</span>
        </div>

        <h3>Question</h3>
        <div style={{ padding: 12, background: "#f3f4f6", borderRadius: 8 }}>{question}</div>

        <h3>Text Answer</h3>
        <textarea value={answerText} onChange={(e) => setAnswerText(e.target.value)} placeholder="Type your answer here..." />
        <div style={{ marginTop: 8 }}>
          <button className="button ghost" onClick={sendTextAnswer}>Submit Text</button>
        </div>

        <h3>Audio + Video Answer</h3>
        <div style={{ display: "flex", gap: 16, alignItems: "flex-start" }}>
          <div>
            <video ref={videoRef} autoPlay muted playsInline style={{ width: 280, height: 190, background: "#000" }}></video>
            <canvas ref={canvasRef} style={{ display: "none" }}></canvas>
          </div>

          <div style={{ flex: 1 }}>
            <p style={{ marginTop: 0, color: "var(--muted)" }}>
              Use your webcam and microphone to record an answer. A snapshot will be captured after recording for facial analysis.
            </p>

            {!isRecording ? (
              <div style={{ display: "flex", gap: 8 }}>
                <button className="button primary" onClick={startMediaRecorder}>Start Recording</button>
                <button className="button" onClick={() => { initMedia().catch(e=>setError(e.message)); }}>Init Camera</button>
              </div>
            ) : (
              <div>
                <button className="button" onClick={stopMediaRecorder}>Stop Recording</button>
                <span style={{ marginLeft: 12, color: "var(--muted)" }}>Recording...</span>
              </div>
            )}

            {error && <p style={{ color: "red" }}>Error: {error}</p>}
          </div>
        </div>

        <h3>Results</h3>
        <p><strong>Transcript:</strong> {transcript || '-'}</p>
        <p><strong>Score:</strong> {score ?? '-'}</p>
      </div>
    </div>
  );
}
