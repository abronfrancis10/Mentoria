import React, { useEffect, useRef, useState } from "react";
import {
  ping,
  startInterview,
  submitTextAnswer,
  submitAudioAnswer,
} from "../api";

export default function Interview({ roleInfo, onComplete }) {
  const [status, setStatus] = useState("checking backend...");
  const [interviewId, setInterviewId] = useState(null);
  const [question, setQuestion] = useState("Preparing your first question...");

  const [answerText, setAnswerText] = useState("");
  const [transcript, setTranscript] = useState("");
  const [score, setScore] = useState(null);
  const [message, setMessage] = useState("");

  const [mediaStream, setMediaStream] = useState(null);
  const [isRecording, setIsRecording] = useState(false);
  const [error, setError] = useState(null);

  const videoRef = useRef(null);
  const canvasRef = useRef(null);
  const mediaRecorderRef = useRef(null);
  const chunksRef = useRef([]);

  useEffect(() => {
    ping()
      .then(() => setStatus("backend available"))
      .catch(() => setStatus("no backend (ok for now)"));

    startInterview({ role: roleInfo?.role || "general", type: "hr" })
      .then((res) => {
        setInterviewId(res.interview_id || "local-test");
        setQuestion(res.first_question || "Tell me about yourself.");
      })
      .catch(() => {
        setQuestion("Tell me about yourself.");
      });
  }, [roleInfo]);

  async function sendText() {
    if (!interviewId) return;
    setMessage("Submitting text answer...");
    try {
      const res = await submitTextAnswer(interviewId, answerText);
      setTranscript(res.transcript || answerText);
      setScore(res.score ?? 0);
      setQuestion(res.next_question || "");
      setMessage("");
    } catch (e) {
      console.error(e);
      setMessage("Failed to submit text answer.");
    }
  }

  async function initMedia() {
    if (!navigator.mediaDevices?.getUserMedia) {
      throw new Error("Media devices API not supported.");
    }
    if (mediaStream) return mediaStream;
    const s = await navigator.mediaDevices.getUserMedia({
      audio: true,
      video: true,
    });
    setMediaStream(s);
    if (videoRef.current) {
      videoRef.current.srcObject = s;
    }
    return s;
  }

  async function startRecording() {
    if (isRecording) return;
    try {
      setError(null);
      const s = await initMedia();
      if (typeof MediaRecorder === "undefined") {
        throw new Error("MediaRecorder not supported in this browser.");
      }

      chunksRef.current = [];
      const recorder = new MediaRecorder(s);
      mediaRecorderRef.current = recorder;

      recorder.ondataavailable = (e) => {
        if (e.data?.size > 0) chunksRef.current.push(e.data);
      };

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
            canvas.width = w;
            canvas.height = h;
            const ctx = canvas.getContext("2d");
            ctx.drawImage(videoEl, 0, 0, w, h);
            const dataUrl = canvas.toDataURL("image/png");
            const response = await fetch(dataUrl);
            snapshotBlob = await response.blob();
          }

          setMessage("Uploading recording...");
          const res = await submitAudioAnswer(
            interviewId || "local-test",
            audioBlob,
            snapshotBlob
          );
          setTranscript(res.transcript || "No transcript");
          setScore(res.score ?? 0);
          setQuestion(res.next_question || "");
          setMessage("");
        } catch (e) {
          console.error(e);
          setMessage("Failed to process recording.");
        }
      };

      recorder.start();
      setIsRecording(true);
      setMessage("Recording...");
    } catch (e) {
      console.error(e);
      setError(e.message);
      setMessage("");
    }
  }

  function stopRecording() {
    if (mediaRecorderRef.current && mediaRecorderRef.current.state !== "inactive") {
      mediaRecorderRef.current.stop();
    }
    setIsRecording(false);
  }

  useEffect(() => {
    return () => {
      if (mediaStream) {
        mediaStream.getTracks().forEach((t) => t.stop());
      }
    };
  }, [mediaStream]);

  function buildFeedback(scoreVal, transcriptVal) {
    const s = scoreVal ?? 0;
    let level = "Beginner";
    if (s >= 8) level = "Advanced";
    else if (s >= 5) level = "Intermediate";

    const improvements = [];
    const avoid = [];

    if (s < 5) improvements.push("Give more detailed, structured answers.");
    if (s < 8) improvements.push("Use more examples from your projects.");
    if (!transcriptVal || transcriptVal.split(" ").length < 30) {
      improvements.push("Try to speak for at least 45–60 seconds per answer.");
    }

    avoid.push("Very short one-line answers.");
    avoid.push("Speaking too fast or too slowly.");
    avoid.push("Using too many filler words like 'um', 'like', 'you know'.");

    return { level, improvements, avoid };
  }

  function handleSubmitAndFinish() {
    const fb = buildFeedback(score, transcript);
    onComplete({
      score: score ?? 0,
      transcript,
      ...fb,
    });
  }

  return (
    <div>
      <h2>Interview</h2>
      <p style={{ color: "var(--muted)", marginBottom: 8 }}>
        Backend: {status} | Role: {roleInfo?.role || "general"}
      </p>

      <h3>Question</h3>
      <div
        style={{
          padding: 12,
          background: "#f3f4f6",
          borderRadius: 8,
          marginBottom: 16,
        }}
      >
        {question}
      </div>

      <h3>Answer (text)</h3>
      <textarea
        value={answerText}
        onChange={(e) => setAnswerText(e.target.value)}
        placeholder="Type your answer here..."
      />
      <div style={{ marginTop: 8, marginBottom: 16 }}>
        <button className="button ghost" onClick={sendText}>
          Submit Text Answer
        </button>
      </div>

      <h3>Answer (audio + video)</h3>
      <div style={{ display: "flex", gap: 16 }}>
        <div>
          <video
            ref={videoRef}
            autoPlay
            muted
            playsInline
            style={{ width: 260, height: 190, background: "#000" }}
          />
          <canvas ref={canvasRef} style={{ display: "none" }} />
        </div>
        <div style={{ flex: 1 }}>
          <p style={{ color: "var(--muted)" }}>
            Use your webcam and mic to record your answer. A snapshot will be
            taken at the end for facial analysis (server-side).
          </p>
          {!isRecording ? (
            <div style={{ display: "flex", gap: 8 }}>
              <button className="button primary" onClick={startRecording}>
                Start Recording
              </button>
              <button
                className="button"
                onClick={() => initMedia().catch((e) => setError(e.message))}
              >
                Init Camera
              </button>
            </div>
          ) : (
            <div>
              <button className="button" onClick={stopRecording}>
                Stop Recording
              </button>
              <span style={{ marginLeft: 8, color: "var(--muted)" }}>
                Recording...
              </span>
            </div>
          )}
          {error && <p style={{ color: "red" }}>Error: {error}</p>}
        </div>
      </div>

      <h3 style={{ marginTop: 20 }}>Live Result (from last answer)</h3>
      <p>
        <strong>Score:</strong> {score ?? "-"}
      </p>
      <p>
        <strong>Transcript:</strong> {transcript || "-"}
      </p>

      <div style={{ marginTop: 16 }}>
        <button
          className="button primary"
          onClick={handleSubmitAndFinish}
          disabled={score === null && !transcript}
        >
          Submit &amp; View Results
        </button>
      </div>
    </div>
  );
}
