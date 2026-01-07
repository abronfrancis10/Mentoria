import React, { useEffect, useRef, useState } from "react";
import {
  ping,
  startInterview,
  submitTextAnswer,
  submitAudioAnswer,
  getNextQuestion, // ✅ ADDED
} from "../api";
import "./Interview.css";

export default function Interview({ roleInfo, onComplete }) {
  const [status, setStatus] = useState("checking backend...");
  const [interviewId, setInterviewId] = useState(null);
  const [question, setQuestion] = useState("Preparing your first question...");

  const [answerText, setAnswerText] = useState("");
  const [transcript, setTranscript] = useState("");
  const [score, setScore] = useState(null);
  const [message, setMessage] = useState("");

  const [answerSubmitted, setAnswerSubmitted] = useState(false); // ✅ ADDED

  const [mediaStream, setMediaStream] = useState(null);
  const [isRecording, setIsRecording] = useState(false);
  const [error, setError] = useState(null);

  const videoRef = useRef(null);
  const canvasRef = useRef(null);
  const mediaRecorderRef = useRef(null);
  const chunksRef = useRef([]);

  // -------------------------
  // INIT INTERVIEW
  // -------------------------
  useEffect(() => {
    ping()
      .then(() => setStatus("backend available"))
      .catch(() => setStatus("no backend (ok for now)"));

    startInterview({ role: roleInfo?.role || "general", type: "hr" })
      .then((res) => {
        setInterviewId(res.interview_id || "local-test");
        setQuestion(res.question || "Tell me about yourself.");
      })
      .catch(() => setQuestion("Tell me about yourself."));
  }, [roleInfo]);

  // -------------------------
  // SUBMIT TEXT ANSWER
  // -------------------------
  async function sendText() {
    if (!interviewId) return;

    setMessage("Submitting text answer...");
    try {
      const res = await submitTextAnswer(interviewId, question, answerText);

      setTranscript(res.candidate_answer || answerText);
      setScore(res.final_score ?? 0);
      setAnswerSubmitted(true); // ✅ ADDED
      setMessage("Answer submitted. Click Next Question.");
    } catch (e) {
      console.error(e);
      setMessage("Failed to submit text answer.");
    }
  }

  // -------------------------
  // NEXT QUESTION (NEW)
  // -------------------------
  async function handleNextQuestion() {
    if (!interviewId) return;

    try {
      const res = await getNextQuestion(interviewId);

      if (res.message === "Interview completed") {
        handleSubmitAndFinish();
        return;
      }

      setQuestion(res.question);
      setAnswerText("");
      setTranscript("");
      setScore(null);
      setAnswerSubmitted(false);
      setMessage("");
    } catch (e) {
      console.error(e);
      setMessage("Failed to load next question.");
    }
  }

  // -------------------------
  // AUDIO LOGIC (UNCHANGED)
  // -------------------------
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
    if (videoRef.current) videoRef.current.srcObject = s;
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
          const audioBlob = new Blob(chunksRef.current, {
            type: "audio/webm",
          });
          chunksRef.current = [];

          setMessage("Uploading recording...");
          const res = await submitAudioAnswer(interviewId, audioBlob);

          setTranscript(res.transcript || "No transcript");
          setScore(res.score ?? 0);
          setAnswerSubmitted(true);
          setMessage("Answer submitted. Click Next Question.");
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
    if (
      mediaRecorderRef.current &&
      mediaRecorderRef.current.state !== "inactive"
    ) {
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

  // -------------------------
  // FINAL SUBMIT (UNCHANGED)
  // -------------------------
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
    onComplete({ score: score ?? 0, transcript, ...fb });
  }

  // -------------------------
  // UI
  // -------------------------
  return (
    <div className="interview-wrapper">
      <div className="interview-card">
        <h2 className="interview-title">Interview</h2>

        <p className="interview-subtitle">
          Backend: {status} | Role: {roleInfo?.role || "general"}
        </p>

        <div className="question-box">{question}</div>

        <div className="video-container">
          <video ref={videoRef} autoPlay muted playsInline />
          <canvas ref={canvasRef} style={{ display: "none" }} />

          <div className="button-row">
            {!isRecording ? (
              <>
                <button className="button primary" onClick={startRecording}>
                  Start Recording
                </button>
                <button className="button" onClick={() => initMedia()}>
                  Init Camera
                </button>
              </>
            ) : (
              <button className="button primary" onClick={stopRecording}>
                Stop Recording
              </button>
            )}
          </div>

          {error && <p className="error-text">{error}</p>}
          {message && <p className="info-text">{message}</p>}
        </div>

        <h3>Optional Text Answer</h3>

        <textarea
          value={answerText}
          onChange={(e) => setAnswerText(e.target.value)}
          placeholder="Type your answer here..."
        />

        <div className="button-row">
          <button className="button ghost" onClick={sendText}>
            Submit Text Answer
          </button>

          <button
            className="button primary"
            onClick={handleNextQuestion}
            disabled={!answerSubmitted}
          >
            Next Question
          </button>

          <button
            className="button primary"
            onClick={handleSubmitAndFinish}
            disabled={score === null && !transcript}
          >
            Submit & View Results
          </button>
        </div>
      </div>
    </div>
  );
}
