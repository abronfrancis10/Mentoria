
import React, { useEffect, useRef, useState } from "react";
import {
  ping,
  startInterview,
  submitTextAnswer,
  submitAudioAnswer,
  getMonitorReport,
  getNextQuestion,
  analyzeFaceFrame,
} from "../api";
import "./Interview.css";

export default function Interview({ roleInfo, onComplete }) {
  const [status, setStatus] = useState("checking backend...");
  const [interviewId, setInterviewId] = useState(null);
  const [question, setQuestion] = useState("Preparing your first question...");
  const [currentDifficulty, setCurrentDifficulty] = useState("medium");
  const [difficultyHistory, setDifficultyHistory] = useState(["medium"]);
  const [questionLevelHistory, setQuestionLevelHistory] = useState([]);
  const [coachingHistory, setCoachingHistory] = useState([]);
  const [coachingBanner, setCoachingBanner] = useState("");

  const [answerText, setAnswerText] = useState("");
  const [score, setScore] = useState(null);
  const [message, setMessage] = useState("");
  const [answerSubmitted, setAnswerSubmitted] = useState(false);
  const [scoreHistory, setScoreHistory] = useState([]);
  const [feedbackHistory, setFeedbackHistory] = useState([]);
  const [transcriptHistory, setTranscriptHistory] = useState([]);
  const [emotionHistory, setEmotionHistory] = useState([]);
  const [textEmotionHistory, setTextEmotionHistory] = useState([]);
  const [faceEmotionHistory, setFaceEmotionHistory] = useState([]);
  const [voiceHistory, setVoiceHistory] = useState([]);
  const [answerQualityHistory, setAnswerQualityHistory] = useState([]);
  const [optimalAlignmentHistory, setOptimalAlignmentHistory] = useState([]);
  const [reviewHistory, setReviewHistory] = useState([]);
  const [latestTextEmotion, setLatestTextEmotion] = useState({
    text_emotion_label: "neutral",
    text_emotion_score: 6,
  });
  const [latestEmotion, setLatestEmotion] = useState({
    emotion_label: "neutral",
    emotion_score: 6,
    warnings: [],
  });
  const [emotionDebug, setEmotionDebug] = useState({
    deepface_error: "",
    mediapipe_error: "",
    deepface_available: true,
    mediapipe_available: true,
  });
  const [emotionStatus, setEmotionStatus] = useState("checking");
  const [warningPopup, setWarningPopup] = useState("");
  const [speechSupported, setSpeechSupported] = useState(true);
  const [speechError, setSpeechError] = useState("");
  const [liveWhisperError, setLiveWhisperError] = useState("");
  const [liveWhisperActive, setLiveWhisperActive] = useState(false);
  const [speechFallbackActive, setSpeechFallbackActive] = useState(false);
  const [micLevel, setMicLevel] = useState(0);
  const [isSpeaking, setIsSpeaking] = useState(false);

  const [mediaStream, setMediaStream] = useState(null);
  const [isRecording, setIsRecording] = useState(false);
  const [error, setError] = useState(null);

  const videoRef = useRef(null);
  const canvasRef = useRef(null);
  const mediaRecorderRef = useRef(null);
  const chunksRef = useRef([]);
  const emotionTimerRef = useRef(null);
  const audioContextRef = useRef(null);
  const analyserRef = useRef(null);
  const micTimerRef = useRef(null);
  const faceDetectorRef = useRef(null);
  const speechRecognitionRef = useRef(null);
  const speechFinalRef = useRef("");
  const shouldAutoRestartSpeechRef = useRef(false);
  const speechRunningRef = useRef(false);
  const speechRestartTimerRef = useRef(null);
  const popupTimerRef = useRef(null);
  const recordingTrackRef = useRef(null);
  const liveTranscribeTimerRef = useRef(null);
  const liveTranscribeBusyRef = useRef(false);
  const lastChunkRef = useRef(null);
  const liveWhisperActiveRef = useRef(false);
  const isRecordingRef = useRef(false);
  const micLevelRef = useRef(0);
  const speechSupportedRef = useRef(true);
  const emotionRequestInFlightRef = useRef(false);
  const lastSpeechResultAtRef = useRef(0);
  const speechWatchdogTimerRef = useRef(null);
  const whisperErrorStreakRef = useRef(0);
  const answerTextRef = useRef("");

  function computeTextEmotion(text) {
    const normalized = String(text || "").toLowerCase();
    const tokens = normalized
      .split(/\s+/)
      .map((item) => item.replace(/[.,!?;:"'()[\]{}]/g, ""))
      .filter(Boolean);
    if (tokens.length === 0) {
      return { label: "neutral", score: 6 };
    }

    const positiveWords = new Set([
      "confident",
      "calm",
      "clear",
      "success",
      "improved",
      "achieved",
      "collaborated",
      "resolved",
      "optimized",
      "delivered",
    ]);
    const negativeWords = new Set([
      "stressed",
      "anxious",
      "angry",
      "fear",
      "failed",
      "panic",
      "confused",
      "upset",
      "frustrated",
      "sad",
    ]);

    let positiveHits = 0;
    let negativeHits = 0;
    tokens.forEach((token) => {
      if (positiveWords.has(token)) positiveHits += 1;
      if (negativeWords.has(token)) negativeHits += 1;
    });

    const sentiment = (positiveHits - negativeHits) / Math.max(tokens.length, 1);
    const score = Math.max(0, Math.min(10, Number((6 + sentiment * 30).toFixed(2))));
    let label = "neutral";
    if (score >= 7.5) label = "positive";
    if (score <= 4.5) label = "negative";
    return { label, score };
  }

  function createSpeechRecognition() {
    const SpeechRecognitionCtor =
      window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognitionCtor) {
      setSpeechSupported(false);
      speechRecognitionRef.current = null;
      return null;
    }
    const recognition = new SpeechRecognitionCtor();
    recognition.continuous = true;
    recognition.interimResults = true;
    recognition.lang = "en-US";

    recognition.onstart = () => {
      speechRunningRef.current = true;
      setSpeechFallbackActive(true);
    };
    recognition.onresult = (event) => {
      let interim = "";
      for (let i = event.resultIndex; i < event.results.length; i += 1) {
        const transcriptPart = event.results[i][0].transcript;
        if (event.results[i].isFinal) {
          speechFinalRef.current += `${transcriptPart} `;
        } else {
          interim += transcriptPart;
        }
      }
      lastSpeechResultAtRef.current = Date.now();
      setAnswerText(`${speechFinalRef.current}${interim}`.trim());
    };
    recognition.onerror = (event) => {
      speechRunningRef.current = false;
      const err = String(event?.error || "speech recognition error");
      // "no-speech" is common in Web Speech API and should auto-recover silently.
      if (err === "no-speech") {
        setSpeechError("");
      } else {
        setSpeechError(err);
      }
      if (isRecordingRef.current && err !== "no-speech" && err !== "aborted") {
        startSpeechCapture(false);
      }
      if (event?.error === "not-allowed" || event?.error === "service-not-allowed") {
        shouldAutoRestartSpeechRef.current = false;
        setSpeechSupported(false);
        return;
      }
      if (shouldAutoRestartSpeechRef.current) {
        if (speechRestartTimerRef.current) {
          clearTimeout(speechRestartTimerRef.current);
        }
        speechRestartTimerRef.current = setTimeout(() => {
          try {
            recognition.start();
          } catch {
            // ignore restart failures
          }
        }, err === "no-speech" ? 120 : 180);
      }
    };
    recognition.onend = () => {
      speechRunningRef.current = false;
      if (shouldAutoRestartSpeechRef.current) {
        if (speechRestartTimerRef.current) {
          clearTimeout(speechRestartTimerRef.current);
        }
        speechRestartTimerRef.current = setTimeout(() => {
          try {
            recognition.start();
          } catch {
            // ignore restart failures
          }
        }, 180);
      }
    };
    speechRecognitionRef.current = recognition;
    setSpeechSupported(true);
    return recognition;
  }

  function teardownSpeechRecognition() {
    shouldAutoRestartSpeechRef.current = false;
    speechRunningRef.current = false;
    if (speechRestartTimerRef.current) {
      clearTimeout(speechRestartTimerRef.current);
      speechRestartTimerRef.current = null;
    }
    const recognition = speechRecognitionRef.current;
    speechRecognitionRef.current = null;
    if (!recognition) return;
    recognition.onstart = null;
    recognition.onresult = null;
    recognition.onerror = null;
    recognition.onend = null;
    try {
      recognition.stop();
    } catch {
      try {
        recognition.abort();
      } catch {
        // ignore teardown failures
      }
    }
  }

  useEffect(() => {
    ping()
      .then(() => setStatus("backend available"))
      .catch(() => setStatus("backend unavailable"));

    if (!roleInfo?.resumeFile) {
      setError("Please upload a resume before starting the interview.");
      return;
    }

    startInterview(
      roleInfo.role || "general",
      roleInfo.resumeFile,
      roleInfo?.userId || "anonymous",
      roleInfo?.totalQuestions || 10,
      roleInfo?.adaptiveContext || null
    )
      .then((res) => {
        if (res.error) {
          setError(res.error);
          return;
        }
        setInterviewId(res.interview_id);
        setQuestion(res.question || "No question returned.");
        const startingDifficulty = String(res.difficulty || "medium");
        setCurrentDifficulty(startingDifficulty);
        setDifficultyHistory([startingDifficulty]);
      })
      .catch((err) => setError(err?.message || "Failed to start interview."));
  }, [roleInfo]);

  useEffect(() => {
    createSpeechRecognition();
    return () => {
      teardownSpeechRecognition();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    liveWhisperActiveRef.current = liveWhisperActive;
  }, [liveWhisperActive]);

  useEffect(() => {
    isRecordingRef.current = isRecording;
  }, [isRecording]);

  useEffect(() => {
    speechSupportedRef.current = speechSupported;
  }, [speechSupported]);

  useEffect(() => {
    answerTextRef.current = answerText;
  }, [answerText]);

  function showWarningPopup(text) {
    if (!text) return;
    setWarningPopup(text);
    if (popupTimerRef.current) {
      clearTimeout(popupTimerRef.current);
    }
    popupTimerRef.current = setTimeout(() => {
      setWarningPopup("");
      popupTimerRef.current = null;
    }, 2200);
  }

  function captureAnswerResult(response, answerTranscript) {
    const answerScore = Number(response?.final_score ?? 0);
    const answerFeedback = (response?.feedback || "").trim();
    const cleanedTranscript = (answerTranscript || "").trim();
    const emotionScore = Number(response?.emotion_score ?? latestEmotion.emotion_score ?? 0);
    const textEmotionScore = Number(
      response?.text_emotion_score ?? response?.emotion_components?.text_score ?? latestTextEmotion.text_emotion_score ?? 0
    );
    const textEmotionLabel = String(
      response?.text_emotion_label ?? response?.emotion_components?.text_label ?? latestTextEmotion.text_emotion_label ?? "neutral"
    );
    const faceEmotionScore = Number(
      response?.face_emotion_score ?? response?.emotion_components?.face_score ?? latestEmotion.emotion_score ?? 0
    );
    const faceEmotionLabel = String(
      response?.face_emotion_label ?? response?.emotion_components?.face_label ?? latestEmotion.emotion_label ?? "unknown"
    );
    const answerQualityScore = Number(response?.answer_quality_score ?? response?.llm_review?.answer_quality_score ?? 0);
    const optimalAlignmentScore = Number(
      response?.optimal_alignment_score ?? response?.llm_review?.optimal_alignment_score ?? 0
    );
    const optimalAlignmentFeedback = String(
      response?.optimal_alignment_feedback ?? response?.llm_review?.optimal_alignment_feedback ?? ""
    ).trim();
    const optimalMismatchPoints = response?.optimal_mismatch_points
      || response?.llm_review?.optimal_mismatch_points
      || [];
    const voiceScore = Number(response?.voice_score ?? 0);
    const nextDifficulty = String(response?.next_difficulty || currentDifficulty || "medium");
    const questionDifficulty = String(response?.current_difficulty || currentDifficulty || "medium");
    const questionNumber = Number(response?.question_number ?? scoreHistory.length + 1);
    const coachingFeedback = response?.coaching_feedback || null;
    const linguisticBreakdown = response?.linguistic_breakdown
      || response?.llm_review?.linguistic_breakdown
      || null;

    setScore(answerScore);
    setMessage(answerFeedback);
    setAnswerSubmitted(true);
    setCurrentDifficulty(nextDifficulty);
    setDifficultyHistory((prev) => [...prev, nextDifficulty]);
    setQuestionLevelHistory((prev) => [
      ...prev,
      {
        question_number: questionNumber,
        difficulty: questionDifficulty,
        score: answerScore,
      },
    ]);

    setScoreHistory((prev) => [...prev, answerScore]);
    if (answerFeedback) {
      setFeedbackHistory((prev) => [...prev, answerFeedback]);
    }
    if (cleanedTranscript) {
      setTranscriptHistory((prev) => [...prev, cleanedTranscript]);
    }
    if (emotionScore > 0) {
      setEmotionHistory((prev) => [...prev, emotionScore]);
    }
    if (textEmotionScore > 0) {
      setTextEmotionHistory((prev) => [...prev, textEmotionScore]);
    }
    if (faceEmotionScore > 0) {
      setFaceEmotionHistory((prev) => [...prev, faceEmotionScore]);
    }
    if (voiceScore > 0) {
      setVoiceHistory((prev) => [...prev, voiceScore]);
    }
    if (answerQualityScore > 0) {
      setAnswerQualityHistory((prev) => [...prev, answerQualityScore]);
    }
    if (optimalAlignmentScore > 0) {
      setOptimalAlignmentHistory((prev) => [...prev, optimalAlignmentScore]);
    }
    setLatestTextEmotion({
      text_emotion_label: textEmotionLabel || "neutral",
      text_emotion_score: textEmotionScore > 0 ? textEmotionScore : 6,
    });
    if (coachingFeedback?.alerts?.length > 0) {
      const alertText = coachingFeedback.alerts.map((item) => item.message).join(" | ");
      setCoachingBanner(alertText);
      setCoachingHistory((prev) => [...prev, coachingFeedback]);
      showWarningPopup(alertText);
    } else if (coachingFeedback) {
      setCoachingBanner(coachingFeedback.instant_tip || "");
      setCoachingHistory((prev) => [...prev, coachingFeedback]);
    }
    if (response?.llm_review) {
      const entry = {
        question: response.question || question,
        transcript: cleanedTranscript,
        ...response.llm_review,
        linguistic_breakdown: linguisticBreakdown,
        final_score: answerScore,
        overall_feedback: answerFeedback,
        emotion_score: emotionScore,
        text_emotion_score: textEmotionScore,
        text_emotion_label: textEmotionLabel,
        face_emotion_score: faceEmotionScore,
        face_emotion_label: faceEmotionLabel,
        answer_quality_score: answerQualityScore,
        optimal_alignment_score: optimalAlignmentScore,
        optimal_alignment_feedback: optimalAlignmentFeedback,
        optimal_mismatch_points: optimalMismatchPoints,
        voice_score: voiceScore,
        optimal_answer: response?.optimal_answer || "",
      };
      setReviewHistory((prev) => {
        const key = `${(entry.question || "").trim().toLowerCase()}|${(entry.transcript || "").trim().toLowerCase()}`;
        if (!key || key === "|") return [...prev, entry];
        const existingIdx = prev.findIndex(
          (item) =>
            `${(item.question || "").trim().toLowerCase()}|${(item.transcript || "").trim().toLowerCase()}` === key
        );
        if (existingIdx === -1) return [...prev, entry];
        const next = [...prev];
        next[existingIdx] = entry;
        return next;
      });
    }
  }

  function buildInterviewSummary() {
    const averageScore =
      scoreHistory.length > 0
        ? Number(
            (scoreHistory.reduce((total, current) => total + current, 0) /
              scoreHistory.length).toFixed(2)
          )
        : Number(score ?? 0);

    const uniqueFeedback = [...new Set(feedbackHistory.filter(Boolean))];
    const strengths = uniqueFeedback
      .filter((item) => /(excellent|good|strong|clear|great|well done)/i.test(item))
      .slice(0, 3);

    const improvements = uniqueFeedback
      .filter((item) => /(improv|needs|avoid|work on|reduce|better)/i.test(item))
      .slice(0, 3);
    const allStrengths = reviewHistory.flatMap((item) => item.strengths || []);
    const allImprovements = reviewHistory.flatMap((item) => item.improvements || []);
    const topStrengths = [...new Set(allStrengths)].slice(0, 5);
    const topImprovements = [...new Set(allImprovements)].slice(0, 5);
    const avgEmotion =
      emotionHistory.length > 0
        ? Number((emotionHistory.reduce((t, v) => t + v, 0) / emotionHistory.length).toFixed(2))
        : 0;
    const avgTextEmotion =
      textEmotionHistory.length > 0
        ? Number((textEmotionHistory.reduce((t, v) => t + v, 0) / textEmotionHistory.length).toFixed(2))
        : 0;
    const avgFaceEmotion =
      faceEmotionHistory.length > 0
        ? Number((faceEmotionHistory.reduce((t, v) => t + v, 0) / faceEmotionHistory.length).toFixed(2))
        : 0;
    const avgVoice =
      voiceHistory.length > 0
        ? Number((voiceHistory.reduce((t, v) => t + v, 0) / voiceHistory.length).toFixed(2))
        : 0;
    const avgAnswerQuality =
      answerQualityHistory.length > 0
        ? Number((answerQualityHistory.reduce((t, v) => t + v, 0) / answerQualityHistory.length).toFixed(2))
        : 0;
    const avgOptimalAlignment =
      optimalAlignmentHistory.length > 0
        ? Number((optimalAlignmentHistory.reduce((t, v) => t + v, 0) / optimalAlignmentHistory.length).toFixed(2))
        : 0;
    const hasPrimaryScores = avgAnswerQuality > 0 || avgVoice > 0 || avgEmotion > 0;
    const overallInterviewScore = hasPrimaryScores
      ? Number(((0.4 * avgAnswerQuality) + (0.3 * avgVoice) + (0.3 * avgEmotion)).toFixed(2))
      : averageScore;
    const suggestedAnswers = [...new Set(reviewHistory
      .map((item) => item.suggested_answer)
      .filter(Boolean)
      .map((item) => String(item).replace(/\s+/g, " ").trim()))]
      .slice(0, 5);
    const reviewedQnA = [];
    const qnaSeen = new Set();
    reviewHistory.forEach((item) => {
      const key = `${(item.question || "").trim().toLowerCase()}|${(item.transcript || "").trim().toLowerCase()}`;
      if (qnaSeen.has(key)) return;
      qnaSeen.add(key);
      reviewedQnA.push({
        question: item.question,
        answer: item.transcript,
        optimal_answer: item.optimal_answer,
        final_score: item.final_score,
        emotion_score: item.emotion_score,
        text_emotion_score: item.text_emotion_score,
        face_emotion_score: item.face_emotion_score,
        answer_quality_score: item.answer_quality_score,
        optimal_alignment_score: item.optimal_alignment_score,
        optimal_alignment_feedback: item.optimal_alignment_feedback,
        optimal_mismatch_points: item.optimal_mismatch_points || [],
        voice_score: item.voice_score,
        llm_score: item.score,
        strengths: item.strengths || [],
        improvements: item.improvements || [],
        suggested_answer: item.suggested_answer || "",
        overall_feedback: item.overall_feedback || "",
        communication_feedback: item.communication_feedback,
      });
    });
    const summarySegments = [];
    if (topStrengths.length > 0) summarySegments.push(`Strengths: ${topStrengths.slice(0, 3).join("; ")}`);
    if (topImprovements.length > 0) summarySegments.push(`Improve: ${topImprovements.slice(0, 3).join("; ")}`);
    if (avgEmotion > 0 || avgVoice > 0) {
      summarySegments.push(
        `Signals: Emotion ${avgEmotion > 0 ? `${avgEmotion}/10` : "-"}, Voice ${avgVoice > 0 ? `${avgVoice}/10` : "-"}.`
      );
    }
    if (avgAnswerQuality > 0 || avgOptimalAlignment > 0) {
      summarySegments.push(
        `Answer quality ${avgAnswerQuality > 0 ? `${avgAnswerQuality}/10` : "-"} | Optimal alignment ${avgOptimalAlignment > 0 ? `${avgOptimalAlignment}/10` : "-"}.`
      );
    }
    const feedbackSummary =
      summarySegments.join(" ") ||
      uniqueFeedback.slice(-2).join(" ") ||
      "Interview completed. Keep practicing concise and role-focused answers.";

    let level = "In Progress";
    if (averageScore >= 8) level = "Advanced";
    else if (averageScore >= 6) level = "Intermediate";
    else level = "Beginner";

    const linguisticBreakdowns = reviewHistory
      .map((item) => item.linguistic_breakdown)
      .filter((item) => item && typeof item === "object");
    const linguisticAverage = (key) => {
      if (linguisticBreakdowns.length === 0) return 0;
      const total = linguisticBreakdowns.reduce((sum, item) => sum + Number(item?.[key] || 0), 0);
      return Number((total / linguisticBreakdowns.length).toFixed(2));
    };
    const linguistic_breakdown = {
      relevance_score: linguisticAverage("relevance_score"),
      structure_score: linguisticAverage("structure_score"),
      grammar_score: linguisticAverage("grammar_score"),
      keyword_match_score: linguisticAverage("keyword_match_score"),
    };
    const linguistic_score = Number(
      (
        (
          linguistic_breakdown.relevance_score
          + linguistic_breakdown.structure_score
          + linguistic_breakdown.grammar_score
          + linguistic_breakdown.keyword_match_score
        ) / 4
      ).toFixed(2)
    );
    const coachingCounts = {};
    coachingHistory.forEach((entry) => {
      (entry?.alerts || []).forEach((alert) => {
        const key = String(alert?.type || "").trim();
        if (!key) return;
        coachingCounts[key] = (coachingCounts[key] || 0) + 1;
      });
    });

    return {
      interview_id: interviewId,
      score: averageScore,
      level,
      feedbackSummary,
      strengths: topStrengths.length > 0 ? topStrengths : strengths,
      improvements: topImprovements.length > 0 ? topImprovements : improvements,
      avoid: [],
      transcript: transcriptHistory.join("\n"),
      feedbackHistory: uniqueFeedback,
      overallInterviewScore,
      emotionScore: avgEmotion,
      textEmotionScore: avgTextEmotion,
      faceEmotionScore: avgFaceEmotion,
      voiceScore: avgVoice,
      answerQualityScore: avgAnswerQuality,
      optimalAlignmentScore: avgOptimalAlignment,
      suggestedAnswers,
      reviewedQnA,
      difficultyHistory,
      questionLevelHistory,
      linguistic_score,
      linguistic_breakdown,
      coaching_summary: {
        total_alerts: coachingHistory.reduce((sum, entry) => sum + Number((entry?.alerts || []).length), 0),
        alert_counts: coachingCounts,
      },
    };
  }

  async function buildInterviewSummaryWithMonitor() {
    const base = buildInterviewSummary();
    if (!interviewId) return base;
    try {
      const report = await getMonitorReport(interviewId);
      return {
        ...base,
        monitorFinalAttentionScore: Number(report?.final_attention_score ?? 0),
        monitorEmotionScorePercent: Number(report?.emotion_score_percent ?? 0),
        issueCounts: report?.issue_counts || {},
        attentionFeedback: report?.attention_feedback || null,
        emotionFeedback: report?.emotion_feedback || null,
        monitorReport: {
          ...report,
          emotion_distribution: report?.emotion_distribution || {},
          dominant_emotion: report?.dominant_emotion || "unknown",
          attention_drop_instances: Number(report?.attention_drop_instances ?? 0),
          average_face_visibility_score: Number(report?.average_face_visibility_score ?? 0),
        },
      };
    } catch {
      return base;
    }
  }

  async function detectBrowserFallbackWarnings(canvas) {
    if (!canvas || !window.FaceDetector) return [];
    if (!faceDetectorRef.current) {
      faceDetectorRef.current = new window.FaceDetector({
        fastMode: true,
        maxDetectedFaces: 3,
      });
    }
    try {
      const faces = await faceDetectorRef.current.detect(canvas);
      const fallbackWarnings = [];
      if (faces.length === 0) {
        fallbackWarnings.push("Face not clear");
      } else {
        if (faces.length > 1) {
          fallbackWarnings.push("Multiple persons detected");
        }
        const mainFace = faces[0].boundingBox;
        const centerY = mainFace.y + mainFace.height / 2;
        if (centerY > canvas.height * 0.62) {
          fallbackWarnings.push("Sit straight, don't slouch");
        }
      }
      return fallbackWarnings;
    } catch {
      return [];
    }
  }

  async function captureEmotionSnapshot() {
    if (!videoRef.current || !canvasRef.current || !interviewId) return latestEmotion;
    if (emotionRequestInFlightRef.current) return latestEmotion;
    const video = videoRef.current;
    if (video.videoWidth === 0 || video.videoHeight === 0) return latestEmotion;
    emotionRequestInFlightRef.current = true;
    const canvas = canvasRef.current;

    try {
      canvas.width = video.videoWidth;
      canvas.height = video.videoHeight;
      const context = canvas.getContext("2d");
      if (!context) return latestEmotion;
      context.drawImage(video, 0, 0, canvas.width, canvas.height);

      const imageBlob = await new Promise((resolve) =>
        canvas.toBlob((blob) => resolve(blob), "image/jpeg", 0.8)
      );
      if (!imageBlob) return latestEmotion;

      const analysis = await analyzeFaceFrame(interviewId, imageBlob);
      const warnings = (analysis.warnings || []).filter(
        (item) => item.toLowerCase() !== "vision dependencies unavailable"
      );
      let finalEmotionLabel = analysis.emotion_label || "neutral";
      let finalEmotionScore = Number(analysis.emotion_score ?? 6);
      let finalWarnings = warnings;

      const backendVisionUnavailable =
        analysis.vision_available !== true
        && !analysis.deepface_available
        && !analysis.mediapipe_available;

      setEmotionDebug({
        deepface_error: String(analysis.deepface_error || ""),
        mediapipe_error:
          String(analysis.mediapipe_error || "").includes("using OpenCV fallback")
            ? ""
            : String(analysis.mediapipe_error || ""),
        deepface_available: Boolean(analysis.deepface_available),
        mediapipe_available: Boolean(analysis.mediapipe_available),
      });

      // Browser fallback when backend vision dependencies are unavailable.
      if (backendVisionUnavailable && window.FaceDetector) {
        setEmotionStatus("fallback");
        const fallbackWarnings = await detectBrowserFallbackWarnings(canvas);
        finalWarnings = [...new Set([...(warnings || []), ...fallbackWarnings])];
        // Keep backend emotion when available; only fallback to neutral if backend has none.
        if (!finalEmotionLabel || finalEmotionLabel === "unknown") {
          finalEmotionLabel = "neutral";
          finalEmotionScore = fallbackWarnings.length === 0 ? 8.0 : 6.0;
        }
      } else if (backendVisionUnavailable) {
        setEmotionStatus("fallback");
      } else {
        setEmotionStatus("ready");
      }

      setLatestEmotion({
        emotion_label: finalEmotionLabel,
        emotion_score: finalEmotionScore,
        warnings: finalWarnings,
      });
      if (analysis?.coaching_feedback?.alerts?.length > 0) {
        const liveAlert = analysis.coaching_feedback.alerts.map((item) => item.message).join(" | ");
        setCoachingBanner(liveAlert);
      } else if (analysis?.coaching_feedback?.instant_tip) {
        setCoachingBanner(String(analysis.coaching_feedback.instant_tip));
      }
      if (finalWarnings.length > 0) {
        showWarningPopup(finalWarnings.join(" | "));
      }
      return {
        ...analysis,
        emotion_label: finalEmotionLabel,
        emotion_score: finalEmotionScore,
        warnings: finalWarnings,
      };
    } catch (err) {
      const fallbackWarnings = await detectBrowserFallbackWarnings(canvas);
      if (fallbackWarnings.length > 0) {
        const fallbackEmotion = {
          emotion_label: latestEmotion?.emotion_label || "neutral",
          emotion_score: Number(latestEmotion?.emotion_score ?? 6),
          warnings: fallbackWarnings,
        };
        setLatestEmotion(fallbackEmotion);
        setEmotionStatus("fallback");
        showWarningPopup(fallbackWarnings.join(" | "));
        setEmotionDebug((prev) => ({
          ...prev,
          mediapipe_error: String(err?.message || "Face analysis request failed"),
        }));
        return fallbackEmotion;
      }
      setEmotionStatus("unavailable");
      setEmotionDebug((prev) => ({
        ...prev,
        mediapipe_error: String(err?.message || "Face analysis request failed"),
      }));
      return latestEmotion;
    } finally {
      emotionRequestInFlightRef.current = false;
    }
  }

  async function handleNextQuestion() {
    // If there is an unsubmitted typed answer, submit it first
    if (!answerSubmitted && answerText.trim()) {
      setMessage("Submitting your answer...");
      const faceAnalysis = await captureEmotionSnapshot();
      const textEmotion = computeTextEmotion(answerText);

      try {
        const res = await submitTextAnswer(interviewId, {
          answer: answerText,
          question,
          role: roleInfo?.role || "General",
          difficulty: currentDifficulty || "medium",
          emotion_score: Number(faceAnalysis?.emotion_score ?? latestEmotion.emotion_score ?? 6),
          emotion_label: faceAnalysis?.emotion_label || latestEmotion.emotion_label || "neutral",
          text_emotion_score: Number(textEmotion.score ?? 6),
          text_emotion_label: textEmotion.label || "neutral",
          face_emotion_score: Number(faceAnalysis?.emotion_score ?? latestEmotion.emotion_score ?? 6),
          face_emotion_label: faceAnalysis?.emotion_label || latestEmotion.emotion_label || "neutral",
        });
        captureAnswerResult(res, answerText);
      } catch (err) {
        console.error("Failed to submit answer:", err);
      }
    }

    const res = await getNextQuestion(interviewId);
    if (res.message === "Interview completed") {
      const finalSummary = await buildInterviewSummaryWithMonitor();
      onComplete(finalSummary);
      return;
    }
    stopSpeechCapture();
    stopLiveWhisperTranscription();
    speechFinalRef.current = "";
    setSpeechError("");
    setLiveWhisperError("");
    setQuestion(res.question);
    if (res?.difficulty) {
      setCurrentDifficulty(String(res.difficulty));
      setDifficultyHistory((prev) => [...prev, String(res.difficulty)]);
    }
    setCoachingBanner("");
    setAnswerText("");
    setScore(null);
    setMessage("");
    setAnswerSubmitted(false);
  }

  async function initMedia() {
    const hasMediaDevices = Boolean(navigator?.mediaDevices?.getUserMedia);
    if (!hasMediaDevices) {
      const secureHint = window.isSecureContext
        ? "This browser does not expose camera/microphone APIs."
        : "Camera and microphone require HTTPS (or localhost).";
      const supportError = `${secureHint} Open the app on https:// or http://localhost.`;
      setError(supportError);
      throw new Error(supportError);
    }

    try {
      const s = await navigator.mediaDevices.getUserMedia({
        audio: true,
        video: true,
      });
      setMediaStream(s);
      videoRef.current.srcObject = s;
      setTimeout(() => {
        captureEmotionSnapshot();
      }, 0);
      if (!emotionTimerRef.current) {
        emotionTimerRef.current = setInterval(() => {
          captureEmotionSnapshot();
        }, 1200);
      }
      return s;
    } catch (err) {
      const errorName = String(err?.name || "");
      let messageText = "Unable to access camera/microphone.";
      if (errorName === "NotAllowedError" || errorName === "PermissionDeniedError") {
        messageText = "Camera/microphone permission denied. Please allow access and try again.";
      } else if (errorName === "NotFoundError" || errorName === "DevicesNotFoundError") {
        messageText = "No camera/microphone device found on this system.";
      } else if (errorName === "NotReadableError" || errorName === "TrackStartError") {
        messageText = "Camera/microphone is busy in another app. Close it and retry.";
      }
      setError(messageText);
      throw new Error(messageText);
    }
  }

  async function ensureLiveMediaStream() {
    const hasLiveAudio =
      mediaStream &&
      mediaStream.getAudioTracks().some((t) => t.readyState === "live" && t.enabled);
    const hasLiveVideo =
      mediaStream &&
      mediaStream.getVideoTracks().some((t) => t.readyState === "live" && t.enabled);

    if (hasLiveAudio && hasLiveVideo) return mediaStream;
    return initMedia();
  }

  function startMicMonitor(stream) {
    try {
      if (!window.AudioContext && !window.webkitAudioContext) return;
      const AudioContextCtor = window.AudioContext || window.webkitAudioContext;
      const audioContext = new AudioContextCtor();
      const analyser = audioContext.createAnalyser();
      analyser.fftSize = 256;
      const source = audioContext.createMediaStreamSource(stream);
      source.connect(analyser);

      audioContextRef.current = audioContext;
      analyserRef.current = analyser;

      const data = new Uint8Array(analyser.frequencyBinCount);
      micTimerRef.current = setInterval(() => {
        analyser.getByteFrequencyData(data);
        const avg = data.reduce((total, value) => total + value, 0) / data.length;
        const normalized = Math.min(100, Math.round((avg / 255) * 180));
        micLevelRef.current = normalized;
        setMicLevel(normalized);
        setIsSpeaking(normalized > 2);
      }, 120);
    } catch {
      micLevelRef.current = 0;
      setMicLevel(0);
      setIsSpeaking(false);
    }
  }

  function stopMicMonitor() {
    if (micTimerRef.current) {
      clearInterval(micTimerRef.current);
      micTimerRef.current = null;
    }
    if (audioContextRef.current) {
      audioContextRef.current.close();
      audioContextRef.current = null;
    }
    analyserRef.current = null;
    micLevelRef.current = 0;
    setMicLevel(0);
    setIsSpeaking(false);
  }

  function startSpeechWatchdog() {
    if (speechWatchdogTimerRef.current) {
      clearInterval(speechWatchdogTimerRef.current);
      speechWatchdogTimerRef.current = null;
    }
    lastSpeechResultAtRef.current = Date.now();
    speechWatchdogTimerRef.current = setInterval(() => {
      if (!isRecordingRef.current) return;
      if (!speechSupportedRef.current) return;
      if (micLevelRef.current <= 6) return;
      if (Date.now() - lastSpeechResultAtRef.current > 4500 && !speechRunningRef.current) {
        startSpeechCapture(false);
      }
    }, 1200);
  }

  function stopSpeechWatchdog() {
    if (speechWatchdogTimerRef.current) {
      clearInterval(speechWatchdogTimerRef.current);
      speechWatchdogTimerRef.current = null;
    }
  }

  function stopLiveWhisperTranscription() {
    liveWhisperActiveRef.current = false;
    whisperErrorStreakRef.current = 0;
    if (liveTranscribeTimerRef.current) {
      clearInterval(liveTranscribeTimerRef.current);
      liveTranscribeTimerRef.current = null;
    }
    liveTranscribeBusyRef.current = false;
    setLiveWhisperActive(false);
    setLiveWhisperError("");
  }

  function startSpeechCapture(resetTranscript = false) {
    // Rebuild recognizer at the moment user starts recording; this is
    // more reliable across browsers than re-instantiating on question change.
    teardownSpeechRecognition();
    createSpeechRecognition();
    if (!speechRecognitionRef.current) return;
    if (resetTranscript) {
      speechFinalRef.current = "";
      setAnswerText("");
    } else {
      speechFinalRef.current = answerText ? `${answerText} ` : "";
    }
    shouldAutoRestartSpeechRef.current = true;
    if (speechRunningRef.current) return;
    try {
      speechRecognitionRef.current.start();
    } catch {
      try {
        speechRecognitionRef.current.abort();
      } catch {
        // ignore abort failures
      }
      if (speechRestartTimerRef.current) {
        clearTimeout(speechRestartTimerRef.current);
      }
      speechRestartTimerRef.current = setTimeout(() => {
        try {
          speechRecognitionRef.current?.start();
        } catch {
          // ignore delayed start failures
        }
      }, 180);
    }
  }

  function stopSpeechCapture() {
    shouldAutoRestartSpeechRef.current = false;
    if (speechRestartTimerRef.current) {
      clearTimeout(speechRestartTimerRef.current);
      speechRestartTimerRef.current = null;
    }
    if (!speechRecognitionRef.current) return;
    try {
      speechRecognitionRef.current.stop();
    } catch {
      try {
        speechRecognitionRef.current.abort();
      } catch {
        // ignore stop errors
      }
    }
    speechRunningRef.current = false;
    setSpeechFallbackActive(false);
  }

  async function startRecording() {
    if (isRecording || answerSubmitted) return;
    setError(null);
    setSpeechError("");
    setLiveWhisperError("");
    let stream;
    try {
      stream = await ensureLiveMediaStream();
    } catch (err) {
      setError(err?.message || "Unable to start recording.");
      return;
    }
    if (!window.MediaRecorder) {
      setError("MediaRecorder is not supported in this browser.");
      return;
    }

    const audioTracks = stream.getAudioTracks();
    if (!audioTracks || audioTracks.length === 0) {
      setError("No microphone track found. Please allow microphone access.");
      return;
    }

    const isolatedTrack = audioTracks[0].clone();
    recordingTrackRef.current = isolatedTrack;
    const audioOnlyStream = new MediaStream([isolatedTrack]);
    const mimeCandidates = [
      "audio/webm;codecs=opus",
      "audio/webm",
      "audio/mp4",
      "",
    ];

    let recorder = null;
    let selectedMime = "";
    for (const candidate of mimeCandidates) {
      try {
        if (candidate && !MediaRecorder.isTypeSupported(candidate)) {
          continue;
        }
        recorder = candidate
          ? new MediaRecorder(audioOnlyStream, { mimeType: candidate })
          : new MediaRecorder(audioOnlyStream);
        selectedMime = candidate || "audio/webm";
        break;
      } catch {
        recorder = null;
      }
    }

    if (!recorder) {
      setError("Could not start audio recording on this browser/device.");
      return;
    }

    mediaRecorderRef.current = recorder;
    chunksRef.current = [];

    recorder.ondataavailable = (e) => {
      if (e.data.size > 0) {
        chunksRef.current.push(e.data);
        lastChunkRef.current = e.data;
      }
    };

    recorder.onstop = async () => {
      if (recordingTrackRef.current) {
        recordingTrackRef.current.stop();
        recordingTrackRef.current = null;
      }
      if (chunksRef.current.length === 0) {
        setError("No audio captured. Please allow microphone access and try again.");
        return;
      }
      const blob = new Blob(chunksRef.current, { type: selectedMime || "audio/webm" });
      setMessage("Analyzing voice, emotion, and answer quality...");
      const faceAnalysis = await captureEmotionSnapshot();
      const textEmotion = computeTextEmotion(answerTextRef.current || "");
      const res = await submitAudioAnswer(interviewId, blob, {
        question,
        role: roleInfo?.role || "General",
        difficulty: currentDifficulty || "medium",
        emotion_score: Number(faceAnalysis?.emotion_score ?? latestEmotion.emotion_score ?? 6),
        emotion_label: faceAnalysis?.emotion_label || latestEmotion.emotion_label || "neutral",
        text_emotion_score: Number(textEmotion.score ?? 6),
        text_emotion_label: textEmotion.label || "neutral",
        face_emotion_score: Number(faceAnalysis?.emotion_score ?? latestEmotion.emotion_score ?? 6),
        face_emotion_label: faceAnalysis?.emotion_label || latestEmotion.emotion_label || "neutral",
        fallbackTranscript: answerTextRef.current,
      });
      captureAnswerResult(res, res.transcript);
      if (res?.transcript) {
        setAnswerText(res.transcript);
        speechFinalRef.current = `${res.transcript} `;
      }
      lastChunkRef.current = null;
    };

    try {
      recorder.start(1000);
    } catch (err) {
      setError(err?.message || "Failed to start recording.");
      return;
    }
    setIsRecording(true);
    isRecordingRef.current = true;
    setMessage("Recording started. Speak clearly.");
    lastSpeechResultAtRef.current = Date.now();
    startMicMonitor(stream);
    startSpeechCapture(true);
    startSpeechWatchdog();
  }

  function stopRecording() {
    if (mediaRecorderRef.current && mediaRecorderRef.current.state !== "inactive") {
      mediaRecorderRef.current.stop();
    }
    setIsRecording(false);
    isRecordingRef.current = false;
    stopMicMonitor();
    stopSpeechWatchdog();
    stopSpeechCapture();
    stopLiveWhisperTranscription();
  }

  useEffect(() => {
    return () => {
      if (emotionTimerRef.current) {
        clearInterval(emotionTimerRef.current);
      }
      if (popupTimerRef.current) {
        clearTimeout(popupTimerRef.current);
      }
      stopMicMonitor();
      stopSpeechWatchdog();
      stopLiveWhisperTranscription();
      teardownSpeechRecognition();
      lastChunkRef.current = null;
      if (recordingTrackRef.current) {
        recordingTrackRef.current.stop();
        recordingTrackRef.current = null;
      }
    };
  }, []);

  useEffect(() => {
    if (!interviewId) return;
    initMedia().catch(() => {
      setError("Please allow camera and microphone permissions for live monitoring.");
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [interviewId]);

  const liveTextEmotion = computeTextEmotion(answerText);
  const displayTextEmotionScore = Number(
    latestTextEmotion.text_emotion_score || liveTextEmotion.score || 6
  );
  const displayTextEmotionLabel = latestTextEmotion.text_emotion_label || liveTextEmotion.label || "neutral";
  const displayFaceEmotionScore = Number(latestEmotion.emotion_score ?? 6);
  const displayCombinedEmotionScore = Number(
    ((0.6 * displayFaceEmotionScore) + (0.4 * displayTextEmotionScore)).toFixed(2)
  );

  return (
    <div className="interview-wrapper">
      <div className="interview-card">
        <h2>Interview</h2>
        <p>Backend: {status}</p>

        <div className="video-container">
          <div className="video-frame">
            <video ref={videoRef} autoPlay muted playsInline />
            <canvas ref={canvasRef} style={{ display: "none" }} />
            <div className="video-overlay">
              <div className="difficulty-chip">Difficulty: {currentDifficulty}</div>
            </div>
          </div>

          <div className="control-panel">
            <div className="question-text">{question}</div>
            {coachingBanner && (
              <div className="warning-banner" style={{ marginTop: 8, background: "#fff7ed", color: "#9a3412" }}>
                Coaching: {coachingBanner}
              </div>
            )}
            {latestEmotion.warnings?.length > 0 && (
              <div className="warning-banner">
                {latestEmotion.warnings.join(" | ")}
              </div>
            )}

            <textarea
              placeholder="Optional text answer..."
              value={answerText}
              onChange={(e) => setAnswerText(e.target.value)}
            />

            <div className="overlay-buttons">
              <button
                onClick={handleNextQuestion}
                disabled={!answerText.trim() && !answerSubmitted}
              >
                {scoreHistory.length >= 4 ? "Finish Interview" : "Next Question"}
              </button>
            </div>
          </div>
        </div>

        <div className="recorder-buttons">
          {!isRecording ? (
            <button onClick={startRecording} disabled={answerSubmitted}>
              Start Recording
            </button>
          ) : (
            <button onClick={stopRecording}>Stop Recording</button>
          )}
        </div>

        {error && <p>{error}</p>}
        {message && <p>{message}</p>}
        {!speechSupported && (
          <p style={{ color: "#b45309" }}>
            Live browser speech-to-text is unavailable in this browser.
          </p>
        )}
        {speechError && (
          <p style={{ color: "#b45309" }}>
            Speech recognition issue: {speechError}
          </p>
        )}
        {liveWhisperActive && (
          <p style={{ color: "#475569" }}>
            Live transcript source: Browser speech
          </p>
        )}
        {speechFallbackActive && !liveWhisperActive && (
          <p style={{ color: "#475569" }}>
            Live transcript source: Browser speech
          </p>
        )}
        {liveWhisperError && (
          <p style={{ color: "#b45309" }}>
            Live speech issue: {liveWhisperError}
          </p>
        )}
        {warningPopup && <div className="warning-popup">{warningPopup}</div>}
        <div className="voice-indicator">
          <div className="voice-meta">
            <strong>Mic Signal:</strong> {isSpeaking ? "Speaking detected" : "Waiting for speech"}
          </div>
          <div className="voice-meter">
            <div className="voice-fill" style={{ width: `${micLevel}%` }} />
          </div>
        </div>
        <p>
          Emotion: {displayCombinedEmotionScore.toFixed(1)}/10
          {` (Face ${displayFaceEmotionScore.toFixed(1)}/10, Text ${displayTextEmotionScore.toFixed(1)}/10)`}
          {` | Face label: ${latestEmotion.emotion_label || "unknown"}, Text label: ${displayTextEmotionLabel}`}
          {latestEmotion.warnings?.length > 0 ? ` | ${latestEmotion.warnings.join(", ")}` : ""}
        </p>
        {emotionStatus === "fallback" && (
          <p style={{ color: "#b45309" }}>
            Using fallback monitoring (warnings active, emotion accuracy limited).
          </p>
        )}
        {(emotionDebug.deepface_error || emotionDebug.mediapipe_error) && (
          <div style={{ marginTop: 8, color: "#92400e", fontSize: 13 }}>
            {!emotionDebug.deepface_available && (
              <p style={{ margin: "4px 0" }}>
                <strong>DeepFace error:</strong> {emotionDebug.deepface_error}
              </p>
            )}
            {!emotionDebug.mediapipe_available && (
              <p style={{ margin: "4px 0" }}>
                <strong>MediaPipe error:</strong> {emotionDebug.mediapipe_error}
              </p>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
