from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from dotenv import load_dotenv
from fastapi import FastAPI, File, Form, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from starlette.concurrency import run_in_threadpool

from app.ai_interview_monitor import monitor as interview_monitor
from app.interview_engine import (
    add_answer_event,
    create_interview,
    get_current_difficulty,
    get_current_question,
    get_interview_state,
    get_next_question,
    inject_question,
    set_current_difficulty,
    submit_answer,
)
from app.routers import evaluation, questions, resume
from app.services.analytics_service import get_session, get_user_trends, save_session
from app.services.answer_pipeline_service import process_answer_pipeline
from app.services.peer_review_service import (
    close_review_request,
    create_review_request,
    get_peer_review_session,
    submit_review,
)
from app.services.question_generation_service import (
    generate_questions_async,
    generate_questions_with_answers_async,
)
from app.services.response_evaluation_service import (
    evaluate_response_async,
    next_difficulty,
)
from app.services.resume_parser_service import parse_resume
from app.services.role_detection_service import refine_role
from app.services.scoring_service import (
    answer_clarity_score,
    combine_emotion_scores,
    emotion_score_from_label,
    final_interview_score,
    normalize_score,
    speech_confidence_score,
)
from app.utils.file_utils import save_upload_file, validate_resume_file

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)


app = FastAPI(
    title="Mentoria API",
    version="4.0.0",
    description="AI-powered interview preparation backend",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(resume.router, prefix="/api/resume", tags=["Resume"])
app.include_router(questions.router, prefix="/api/questions", tags=["Questions"])
app.include_router(evaluation.router, prefix="/api/evaluation", tags=["Evaluation"])


@app.on_event("startup")
async def startup_event():
    """
    Pre-load AI models on startup to ensure zero-latency during the demo.
    Prioritizes Emotion, Attention, and LLM clients.
    """
    logger.info("Initializing AI components for demo readiness...")
    
    # 1. Load MediaPipe & DeepFace for Attention/Emotion
    try:
        # Run in threadpool to not block startup if slow
        await run_in_threadpool(interview_monitor._ensure_mediapipe_models)
        await run_in_threadpool(interview_monitor._ensure_deepface)
        logger.info("Emotion and Attention modules initialized.")
    except Exception as e:
        logger.error(f"Failed to pre-load vision models: {e}")

    # 2. Warm up LLM Client (checks env and API keys)
    try:
        from app.services.async_llm_client import async_llm_client
        logger.info(f"LLM Client ready. Primary Ollama Model: {async_llm_client.ollama_model}")
        
        # Verify Ollama connection with a tiny probe
        logger.info("Probing Ollama connection...")
        probe_res = await async_llm_client.generate_ollama("hi", model=async_llm_client.ollama_model)
        if probe_res:
            logger.info("Ollama probe successful.")
        else:
            logger.warning("Ollama probe returned empty or failed.")
    except Exception as e:
        logger.warning(f"Ollama warm-up failed: {e}. System will use fallbacks.")


class LegacyQuestionRequest(BaseModel):
    role: str
    skills: list[str]
    difficulty: str = "medium"


class LegacyEvaluationRequest(BaseModel):
    role: str
    question: str
    answer: str
    difficulty: str = "medium"


class AdaptiveDifficultyRequest(BaseModel):
    score: float
    current_difficulty: str = "medium"


class TextAnswerRequest(BaseModel):
    answer: str
    question: str = ""
    role: str = "General"
    difficulty: str = "medium"
    emotion_score: Optional[float] = None
    emotion_label: str = ""
    text_emotion_score: Optional[float] = None
    text_emotion_label: str = ""
    face_emotion_score: Optional[float] = None
    face_emotion_label: str = ""
    voice_score: Optional[float] = None
    filler_word_count: Optional[int] = None
    words_per_minute: Optional[float] = None
    speech_rate: Optional[float] = None
    pause_count: Optional[int] = None
    long_pause_count: Optional[int] = None
    pause_frequency: Optional[float] = None
    tone_variation_score: Optional[float] = None
    clarity_score: Optional[float] = None
    speech_confidence_score: Optional[float] = None
    answer_clarity_score: Optional[float] = None


class FinalizeSessionRequest(BaseModel):
    user_id: str = "anonymous"
    role: str = ""


class PeerReviewRequestCreate(BaseModel):
    session_id: str
    requester_id: str = "anonymous"
    focus_areas: str = ""


class PeerReviewSubmitRequest(BaseModel):
    session_id: str
    reviewer_id: str = "anonymous"
    reviewer_name: str
    session_owner_id: str = ""
    overall_rating: int = Field(..., ge=1, le=5)
    communication_rating: int = Field(..., ge=1, le=5)
    technical_rating: int = Field(..., ge=1, le=5)
    comments: str
    tags: list[str] = []


class PeerReviewCloseRequest(BaseModel):
    session_id: str
    requester_id: str = ""


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _safe_float(value: Optional[float], default: float = 0.0) -> float:
    try:
        return float(value if value is not None else default)
    except Exception:
        return default


def _safe_int(value: Optional[int], default: int = 0) -> int:
    try:
        return int(value if value is not None else default)
    except Exception:
        return default


def _emotion_score_from_label(label: str) -> float:
    return emotion_score_from_label(label)


def _text_emotion_from_text(text: str) -> Dict[str, float | str]:
    lowered = str(text or "").lower()
    tokens = [t.strip(".,!?;:\"'()[]{}") for t in lowered.split()]
    if not tokens:
        return {"label": "neutral", "score": 6.0}

    positive_words = {
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
    }
    negative_words = {
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
    }

    pos_hits = sum(1 for t in tokens if t in positive_words)
    neg_hits = sum(1 for t in tokens if t in negative_words)
    sentiment = (pos_hits - neg_hits) / max(len(tokens), 1)
    score = 6.0 + (sentiment * 30.0)
    score = max(0.0, min(10.0, round(score, 2)))

    if score >= 7.5:
        label = "positive"
    elif score <= 4.5:
        label = "negative"
    else:
        label = "neutral"
    return {"label": label, "score": score}


def _normalize_emotion_score(value: Optional[float], fallback: float) -> float:
    return normalize_score(value, fallback)


def _build_coaching_feedback(
    filler_count: int,
    attention_score: float,
    speech_rate: float,
    long_pause_count: int,
) -> Dict:
    alerts = []
    if filler_count >= 3:
        alerts.append(
            {
                "type": "filler_words",
                "severity": "medium",
                "message": "Reduce filler words for clearer delivery.",
            }
        )
    if attention_score < 70:
        alerts.append(
            {
                "type": "attention_low",
                "severity": "high",
                "message": "Maintain stronger eye contact and stable posture.",
            }
        )
    if speech_rate < 90:
        alerts.append(
            {
                "type": "speech_rate_low",
                "severity": "medium",
                "message": "Speak slightly faster to maintain interview momentum.",
            }
        )
    elif speech_rate > 160:
        alerts.append(
            {
                "type": "speech_rate_high",
                "severity": "medium",
                "message": "Slow down to improve clarity and confidence.",
            }
        )
    if long_pause_count >= 2:
        alerts.append(
            {
                "type": "long_pauses",
                "severity": "medium",
                "message": "Use shorter pauses and keep answer flow continuous.",
            }
        )

    base = 10.0
    penalties = {
        "filler_words": 1.6,
        "attention_low": 2.0,
        "speech_rate_low": 1.2,
        "speech_rate_high": 1.2,
        "long_pauses": 1.5,
    }
    for alert in alerts:
        base -= penalties.get(alert["type"], 0.8)
    coaching_score = max(0.0, round(base, 2))

    if not alerts:
        instant_tip = "Great delivery. Keep the same structure and confidence."
    elif any(a["type"] == "attention_low" for a in alerts):
        instant_tip = "Re-center with eye contact and posture before continuing."
    elif any(a["type"].startswith("speech_rate") for a in alerts):
        instant_tip = "Adjust your speaking pace and keep a steady rhythm."
    else:
        instant_tip = "Pause briefly, then continue with a structured answer."

    return {
        "alerts": alerts,
        "instant_tip": instant_tip,
        "coaching_score": coaching_score,
    }


def _overall_interview_score(
    answer_clarity: float, speech_confidence: float, emotion_score: float
) -> float:
    return final_interview_score(
        emotion_score=emotion_score,
        speech_confidence=speech_confidence,
        answer_clarity=answer_clarity,
    )


def _parse_adaptive_context(raw: str) -> Dict[str, Any]:
    text = str(raw or "").strip()
    if not text:
        return {}
    try:
        parsed = json.loads(text)
    except Exception:
        return {}
    return parsed if isinstance(parsed, dict) else {}


def _score_to_level(score: float) -> str:
    normalized = _safe_float(score, 0.0)
    if normalized >= 8.0:
        return "Advanced"
    if normalized >= 6.0:
        return "Intermediate"
    return "Beginner"


def _level_to_difficulty(level: str) -> str:
    normalized = str(level or "").strip().lower()
    if normalized in {"advanced", "hard"}:
        return "hard"
    if normalized in {"intermediate", "medium"}:
        return "medium"
    if normalized in {"beginner", "easy"}:
        return "easy"
    return "medium"


def _difficulty_to_level(difficulty: str) -> str:
    normalized = str(difficulty or "").strip().lower()
    if normalized == "hard":
        return "Advanced"
    if normalized == "easy":
        return "Beginner"
    return "Intermediate"


def _derive_initial_difficulty(adaptive_profile: Dict[str, Any]) -> str:
    if not adaptive_profile:
        return "medium"

    previous_score = _safe_float(
        adaptive_profile.get("previous_overall_interview_score"), 0.0
    )
    average_score = _safe_float(
        adaptive_profile.get("average_overall_interview_score"), previous_score
    )
    sessions_count = _safe_int(adaptive_profile.get("sessions_count"), 0)
    has_history = sessions_count > 0 or previous_score > 0.0 or average_score > 0.0
    if not has_history:
        return "medium"

    recommended_level = str(adaptive_profile.get("recommended_level", "")).strip()
    if recommended_level:
        return _level_to_difficulty(recommended_level)

    latest_level = str(adaptive_profile.get("latest_level", "")).strip()
    if latest_level:
        return _level_to_difficulty(latest_level)

    return _level_to_difficulty(
        _score_to_level(average_score if average_score > 0 else previous_score)
    )


def _role_focus_points(role: str, skills: list[str]) -> list[str]:
    role_lower = str(role or "").lower()
    points: list[str] = []

    if any(token in role_lower for token in ("frontend", "ui", "ux", "react")):
        points.extend(
            [
                "component design and state management",
                "performance optimization and rendering strategy",
                "accessibility and responsive implementation",
                "debugging browser/runtime issues",
            ]
        )
    elif any(
        token in role_lower for token in ("backend", "api", "server", "java", "python")
    ):
        points.extend(
            [
                "api design and contract clarity",
                "database design, query efficiency, and data integrity",
                "scalability, reliability, and failure handling",
                "security and production debugging",
            ]
        )
    elif any(token in role_lower for token in ("data", "ml", "machine learning", "ai")):
        points.extend(
            [
                "data preparation and feature engineering",
                "model selection and evaluation metrics",
                "error analysis and model improvement strategy",
                "deployment and monitoring of model performance",
            ]
        )
    elif any(token in role_lower for token in ("devops", "sre", "cloud")):
        points.extend(
            [
                "ci/cd pipeline reliability",
                "infrastructure as code and environment consistency",
                "observability, incident response, and root-cause analysis",
                "cost-performance-security trade-offs in cloud systems",
            ]
        )
    else:
        points.extend(
            [
                "problem decomposition and prioritization",
                "trade-off analysis with concrete justification",
                "communication clarity under constraints",
                "debugging with measurable validation",
            ]
        )

    for skill in skills[:4]:
        points.append(f"practical application of {skill}")

    seen: set[str] = set()
    deduped: list[str] = []
    for item in points:
        key = str(item).strip().lower()
        if not key or key in seen:
            continue
        seen.add(key)
        deduped.append(str(item).strip())
    return deduped[:8]


def _aggregate_session(
    interview_id: str, user_id: str, fallback_role: str = ""
) -> Dict:
    state = get_interview_state(interview_id)
    if not state:
        raise HTTPException(status_code=404, detail="Invalid interview id")

    answer_events = list(state.get("answer_events") or [])
    report = interview_monitor.get_report(interview_id)

    def avg(key: str, default: float = 0.0) -> float:
        values = [
            float(item.get(key, 0.0))
            for item in answer_events
            if item.get(key) is not None
        ]
        if not values:
            return float(default)
        return round(sum(values) / len(values), 2)

    filler_total = sum(
        int(item.get("filler_word_count", 0) or 0) for item in answer_events
    )
    pause_total = sum(int(item.get("pause_count", 0) or 0) for item in answer_events)
    breakdown_keys = [
        "relevance_score",
        "structure_score",
        "grammar_score",
        "keyword_match_score",
    ]
    linguistic_breakdown = {}
    for key in breakdown_keys:
        values = [
            float((item.get("linguistic_breakdown") or {}).get(key, 0.0))
            for item in answer_events
            if isinstance(item.get("linguistic_breakdown"), dict)
        ]
        linguistic_breakdown[key] = (
            round(sum(values) / len(values), 2) if values else 0.0
        )

    alert_counts: Dict[str, int] = {}
    total_alerts = 0
    for event in answer_events:
        coaching = event.get("coaching_feedback") or {}
        for alert in coaching.get("alerts") or []:
            alert_type = str(alert.get("type", "")).strip()
            if not alert_type:
                continue
            alert_counts[alert_type] = alert_counts.get(alert_type, 0) + 1
            total_alerts += 1

    role = str(state.get("role") or fallback_role or "General")
    overall_score = avg("overall_score", 0.0)
    linguistic_score = avg(
        "linguistic_score", round(sum(linguistic_breakdown.values()) / 4.0, 2)
    )
    emotion_score = avg("emotion_score", 0.0)
    text_emotion_score = avg("text_emotion_score", 0.0)
    face_emotion_score = avg("face_emotion_score", 0.0)
    speech_confidence = avg("speech_confidence_score", avg("voice_score", 0.0))
    answer_clarity = avg("answer_clarity_score", avg("answer_quality_score", 0.0))
    voice_score = speech_confidence
    answer_quality_score = answer_clarity
    optimal_alignment_score = avg("optimal_alignment_score", 0.0)
    attention_score = round(float(report.get("final_attention_score", 0.0)), 2)
    overall_interview_score = _overall_interview_score(
        answer_clarity=answer_clarity,
        speech_confidence=speech_confidence,
        emotion_score=emotion_score,
    )

    session_payload = {
        "user_id": user_id or str(state.get("user_id", "anonymous")),
        "role": role,
        "started_at": str(state.get("started_at") or _now_iso()),
        "completed_at": _now_iso(),
        "overall_score": overall_score,
        "overall_interview_score": overall_interview_score,
        "linguistic_score": linguistic_score,
        "answer_quality_score": answer_quality_score,
        "answer_clarity_score": answer_clarity,
        "optimal_alignment_score": optimal_alignment_score,
        "emotion_score": emotion_score,
        "text_emotion_score": text_emotion_score,
        "face_emotion_score": face_emotion_score,
        "attention_score": attention_score,
        "voice_score": voice_score,
        "speech_confidence_score": speech_confidence,
        "filler_word_count": int(filler_total),
        "pause_count": int(pause_total),
        "speech_rate": avg("speech_rate", avg("words_per_minute", 0.0)),
        "tone_variation_score": avg("tone_variation_score", 0.0),
        "pause_frequency": avg("pause_frequency", 0.0),
        "clarity_score": avg("clarity_score", 0.0),
        "linguistic_breakdown": linguistic_breakdown,
        "difficulty_history": list(state.get("difficulty_history") or []),
        "question_level_history": list(state.get("question_level_history") or []),
        "difficulty_transition_counts": dict(
            state.get("difficulty_transition_counts") or {}
        ),
        "final_difficulty_reached": str(
            state.get("final_difficulty_reached") or "medium"
        ),
        "monitor_report": {
            "emotion_distribution": dict(report.get("emotion_distribution") or {}),
            "dominant_emotion": report.get("dominant_emotion", "unknown"),
            "attention_drop_instances": int(report.get("attention_drop_instances", 0)),
            "average_face_visibility_score": float(
                report.get("average_face_visibility_score", 0.0)
            ),
            "final_attention_score": float(report.get("final_attention_score", 0.0)),
            "emotion_score_percent": float(report.get("emotion_score_percent", 0.0)),
            "issue_counts": dict(report.get("issue_counts") or {}),
            "attention_feedback": dict(report.get("attention_feedback") or {}),
            "emotion_feedback": dict(report.get("emotion_feedback") or {}),
        },
        "coaching_summary": {
            "total_alerts": int(total_alerts),
            "alert_counts": alert_counts,
        },
        "answer_events": answer_events,
        "timestamp": _now_iso(),
    }
    return session_payload


@app.get("/")
def health() -> dict:
    return {"status": "Mentoria backend running"}


@app.post("/upload-resume")
async def upload_resume_legacy(
    role: str = Form(...), resume: UploadFile = File(...)
) -> dict:
    extension = validate_resume_file(resume)
    path = save_upload_file(resume, "uploads")
    text, skills = parse_resume(path, extension)
    refined = refine_role(role, skills)
    return {
        "role_input": role,
        "refined_role": refined,
        "skills": skills,
        "text_preview": text[:600],
    }


@app.post("/generate-questions")
async def generate_questions_legacy(payload: LegacyQuestionRequest) -> dict:
    refined = refine_role(payload.role, payload.skills)
    result = await generate_questions_async(refined, payload.skills, payload.difficulty)
    return {
        "technical": result.get("technical", []),
        "behavioral": result.get("behavioral", []),
        "scenario": result.get("scenario", []),
    }


@app.post("/evaluate-response")
async def evaluate_response_legacy(payload: LegacyEvaluationRequest) -> dict:
    return await evaluate_response_async(
        role=payload.role,
        question=payload.question,
        answer=payload.answer,
        difficulty=payload.difficulty,
    )


@app.post("/adaptive-difficulty")
def adaptive_difficulty_legacy(payload: AdaptiveDifficultyRequest) -> dict:
    return {"next_difficulty": next_difficulty(payload.score)}


@app.post("/start-interview")
async def start_interview(
    role: str = Form(...),
    resume: UploadFile = File(...),
    user_id: str = Form("anonymous"),
    adaptive_context: str = Form(""),
) -> dict:
    total_questions = 5
    extension = validate_resume_file(resume)
    path = save_upload_file(resume, "uploads")
    _, skills = parse_resume(path, extension)
    refined = refine_role(role, skills)
    adaptive_profile = _parse_adaptive_context(adaptive_context)
    adaptive_profile["role_focus_points"] = _role_focus_points(refined, skills)
    adaptive_history_available = (
        _safe_int(adaptive_profile.get("sessions_count"), 0) > 0
        or _safe_float(adaptive_profile.get("previous_overall_interview_score"), 0.0)
        > 0.0
        or _safe_float(adaptive_profile.get("average_overall_interview_score"), 0.0)
        > 0.0
    )

    total_questions = max(1, min(int(total_questions or 10), 20))
    initial_difficulty = _derive_initial_difficulty(adaptive_profile)

    # Generate ONLY the first question to start instantly
    first_qs = await generate_questions_with_answers_async(
        refined,
        skills,
        initial_difficulty,
        count=1,
    )

    question_bank = {
        "easy": [],
        "medium": [],
        "hard": [],
    }
    if first_qs:
        question_bank[initial_difficulty] = first_qs

    interview_id = create_interview(
        question_bank,
        role=refined,
        skills=skills,
        user_id=user_id,
        total_questions=total_questions,
        initial_difficulty=initial_difficulty,
    )
    first = get_next_question(interview_id)
    if first.get("error"):
        raise HTTPException(status_code=400, detail=str(first["error"]))

    return {
        "interview_id": interview_id,
        "role": refined,
        "skills": skills,
        "total_questions": int(first.get("total_questions", total_questions)),
        "question": first.get("question"),
        "question_number": int(first.get("question_number", 1)),
        "difficulty": str(first.get("difficulty", "medium")),
        "recommended_level": _difficulty_to_level(initial_difficulty),
        "adaptive_context_applied": adaptive_history_available,
    }


@app.get("/next-question/{interview_id}")
async def next_question(interview_id: str) -> dict:
    state = get_interview_state(interview_id)
    if not state:
        raise HTTPException(status_code=404, detail="Interview not found")
        
    if state["answered_count"] >= state["total_questions"]:
        return {"message": "Interview completed"}

    # Attempt to fetch next question from engine
    next_q = get_next_question(interview_id)
    if next_q.get("message") == "Interview completed" and state["answered_count"] < state["total_questions"]:
        # The engine's bank is empty but we haven't reached total questions. Generate one dynamically!
        difficulty = state.get("current_difficulty", "medium")
        new_qs = await generate_questions_with_answers_async(
            state.get("role", "General"),
            state.get("skills", []),
            difficulty,
            count=1
        )
        if new_qs:
            inject_question(interview_id, new_qs[0])
            next_q = get_next_question(interview_id)

    return next_q


@app.post("/submit-answer/{interview_id}")
async def submit_answer_text(interview_id: str, payload: TextAnswerRequest) -> dict:
    transcript = str(payload.answer or "").strip()
    if not transcript:
        raise HTTPException(status_code=400, detail="Answer is required")

    current = get_current_question(interview_id)
    state = get_interview_state(interview_id)
    if not state or not current:
        raise HTTPException(
            status_code=400, detail="No active question for this interview"
        )

    question_text = str(
        current.get("question") or payload.question or "Interview question"
    )
    optimal_reference = str(current.get("optimal_answer") or "").strip()
    current_difficulty = str(
        current.get("difficulty")
        or get_current_difficulty(interview_id)
        or payload.difficulty
        or "medium"
    )
    question_number = int(state.get("answered_count", 0)) + 1

    llm_review = await evaluate_response_async(
        role=payload.role or str(state.get("role") or "General"),
        question=question_text,
        answer=transcript,
        difficulty=current_difficulty,
        optimal_answer=optimal_reference,
    )
    llm_score = _safe_float(llm_review.get("score"), 6.0)
    linguistic_score = _safe_float(llm_review.get("linguistic_score"), llm_score)
    optimal_alignment_score = _safe_float(
        llm_review.get("optimal_alignment_score"), 0.0
    )
    optimal_alignment_feedback = str(
        llm_review.get("optimal_alignment_feedback") or ""
    ).strip()
    optimal_mismatch_points = list(llm_review.get("optimal_mismatch_points") or [])
    linguistic_breakdown = dict(llm_review.get("linguistic_breakdown") or {})
    relevance_score = _safe_float(linguistic_breakdown.get("relevance_score"), 0.0)
    structure_score = _safe_float(linguistic_breakdown.get("structure_score"), 0.0)
    grammar_score = _safe_float(linguistic_breakdown.get("grammar_score"), 0.0)
    keyword_match_score = _safe_float(
        linguistic_breakdown.get("keyword_match_score"), 0.0
    )
    llm_answer_quality = _safe_float(
        llm_review.get("answer_quality_score"), linguistic_score
    )

    provided_voice_score = _safe_float(payload.voice_score, 0.0)
    provided_speech_confidence = _safe_float(payload.speech_confidence_score, 0.0)
    speech_rate = _safe_float(
        payload.speech_rate, _safe_float(payload.words_per_minute, 0.0)
    )
    filler_count = _safe_int(payload.filler_word_count, 0)
    pause_count = _safe_int(payload.pause_count, 0)
    long_pause_count = _safe_int(payload.long_pause_count, 0)
    pause_frequency = _safe_float(payload.pause_frequency, 0.0)
    tone_variation_score = _safe_float(payload.tone_variation_score, 0.0)
    clarity_score = _safe_float(payload.clarity_score, 0.0)

    text_emotion_data = _text_emotion_from_text(transcript)
    text_emotion_label = (
        str(payload.text_emotion_label or text_emotion_data["label"]).strip().lower()
        or "neutral"
    )
    text_emotion_score = _normalize_emotion_score(
        payload.text_emotion_score,
        _safe_float(
            text_emotion_data["score"], _emotion_score_from_label(text_emotion_label)
        ),
    )

    face_emotion_label = (
        str(payload.face_emotion_label or payload.emotion_label or "").strip().lower()
    )
    face_fallback = (
        _emotion_score_from_label(face_emotion_label) if face_emotion_label else 0.0
    )
    face_emotion_score = _normalize_emotion_score(
        payload.face_emotion_score
        if payload.face_emotion_score is not None
        else payload.emotion_score,
        face_fallback,
    )
    has_face_emotion = (
        payload.face_emotion_score is not None
        or payload.emotion_score is not None
        or bool(face_emotion_label)
    )
    if not has_face_emotion:
        face_emotion_score = 0.0
        face_emotion_label = "unknown"

    emotion_score = combine_emotion_scores(
        face_emotion_score=face_emotion_score,
        text_emotion_score=text_emotion_score,
        has_face_emotion=has_face_emotion,
    )
    emotion_label = (
        face_emotion_label
        if has_face_emotion and face_emotion_label
        else text_emotion_label
    )

    answer_clarity = answer_clarity_score(
        relevance_score=relevance_score,
        structure_score=structure_score,
        grammar_score=grammar_score,
        keyword_match_score=keyword_match_score,
        fallback_linguistic_score=linguistic_score,
    )
    if provided_speech_confidence > 0:
        provided_voice_score = provided_speech_confidence
    provided_answer_clarity = _safe_float(payload.answer_clarity_score, 0.0)
    if provided_answer_clarity > 0:
        answer_clarity = round(
            (0.7 * answer_clarity)
            + (0.3 * normalize_score(provided_answer_clarity, answer_clarity)),
            2,
        )

    answer_quality_score = round(
        (0.75 * answer_clarity) + (0.25 * optimal_alignment_score), 2
    )
    if answer_quality_score <= 0:
        answer_quality_score = llm_answer_quality

    speech_confidence = speech_confidence_score(
        provided_voice_score=provided_voice_score if provided_voice_score > 0 else None,
        filler_word_count=filler_count,
        speech_rate=speech_rate,
        long_pause_count=long_pause_count,
        pause_frequency=pause_frequency,
        tone_variation_score=tone_variation_score,
        clarity_score=clarity_score,
    )
    voice_score = speech_confidence

    emotion_components = {
        "face_score": round(face_emotion_score, 2),
        "face_label": face_emotion_label or "unknown",
        "text_score": round(text_emotion_score, 2),
        "text_label": text_emotion_label,
        "combined_score": round(emotion_score, 2),
    }
    attention_report = interview_monitor.get_report(interview_id)
    attention_score_100 = _safe_float(
        attention_report.get("final_attention_score"), 0.0
    )
    overall_score = final_interview_score(
        emotion_score=emotion_score,
        speech_confidence=speech_confidence,
        answer_clarity=answer_clarity,
    )
    
    # Use Strict Mode NEXT_STEP_CONTROLLER for difficulty transitions
    from app.services.response_evaluation_service import get_next_step_async
    previous_scores = [float(e.get("overall_score", 0)) for e in (state.get("answer_events") or [])]
    # Include current score in the list for the controller
    previous_scores.append(overall_score)
    
    next_step_data = await get_next_step_async(
        previous_scores=previous_scores[-3:], # last 3 as per rules
        current_difficulty=current_difficulty
    )
    next_diff = next_step_data.get("next_difficulty", next_difficulty(overall_score)).lower()

    coaching_feedback = _build_coaching_feedback(
        filler_count=filler_count,
        attention_score=attention_score_100,
        speech_rate=speech_rate,
        long_pause_count=long_pause_count,
    )

    optimal = submit_answer(interview_id, transcript) or optimal_reference
    set_current_difficulty(interview_id, next_diff)

    answer_event = {
        "timestamp": _now_iso(),
        "question_number": question_number,
        "question": question_text,
        "difficulty": current_difficulty,
        "candidate_answer": transcript,
        "optimal_answer": optimal,
        "overall_score": overall_score,
        "llm_score": round(llm_score, 2),
        "linguistic_score": round(linguistic_score, 2),
        "answer_clarity_score": round(answer_clarity, 2),
        "answer_quality_score": round(answer_quality_score, 2),
        "optimal_alignment_score": round(optimal_alignment_score, 2),
        "optimal_alignment_feedback": optimal_alignment_feedback,
        "optimal_mismatch_points": optimal_mismatch_points,
        "linguistic_breakdown": linguistic_breakdown,
        "emotion_score": round(emotion_score, 2),
        "text_emotion_score": round(text_emotion_score, 2),
        "text_emotion_label": text_emotion_label,
        "face_emotion_score": round(face_emotion_score, 2),
        "face_emotion_label": face_emotion_label or "unknown",
        "attention_score": round(attention_score_100, 2),
        "voice_score": round(voice_score, 2),
        "speech_confidence_score": round(speech_confidence, 2),
        "filler_word_count": filler_count,
        "pause_count": pause_count,
        "long_pause_count": long_pause_count,
        "pause_frequency": round(pause_frequency, 2),
        "speech_rate": round(speech_rate, 2),
        "tone_variation_score": round(tone_variation_score, 2),
        "clarity_score": round(clarity_score, 2),
        "coaching_feedback": coaching_feedback,
    }
    add_answer_event(interview_id, answer_event)

    feedback = str(llm_review.get("communication_feedback") or "Answer evaluated.")
    return {
        "final_score": overall_score,
        "overall_score": overall_score,
        "feedback": feedback,
        "optimal_answer": optimal,
        "candidate_answer": transcript,
        "question": question_text,
        "question_number": question_number,
        "current_difficulty": current_difficulty,
        "next_difficulty": next_diff,
        "emotion_score": round(emotion_score, 2),
        "emotion_label": emotion_label or "neutral",
        "emotion_components": emotion_components,
        "text_emotion_score": round(text_emotion_score, 2),
        "text_emotion_label": text_emotion_label,
        "face_emotion_score": round(face_emotion_score, 2),
        "face_emotion_label": face_emotion_label or "unknown",
        "attention_score": round(attention_score_100, 2),
        "voice_score": round(voice_score, 2),
        "filler_word_count": filler_count,
        "words_per_minute": round(speech_rate, 2),
        "speech_rate": round(speech_rate, 2),
        "pause_count": pause_count,
        "long_pause_count": long_pause_count,
        "pause_frequency": round(pause_frequency, 2),
        "tone_variation_score": round(tone_variation_score, 2),
        "clarity_score": round(clarity_score, 2),
        "linguistic_score": round(linguistic_score, 2),
        "answer_clarity_score": round(answer_clarity, 2),
        "answer_quality_score": round(answer_quality_score, 2),
        "optimal_alignment_score": round(optimal_alignment_score, 2),
        "optimal_alignment_feedback": optimal_alignment_feedback,
        "optimal_mismatch_points": optimal_mismatch_points,
        "linguistic_breakdown": linguistic_breakdown,
        "speech_confidence_score": round(speech_confidence, 2),
        "scoring_components": {
            "emotion_score": round(emotion_score, 2),
            "speech_confidence_score": round(speech_confidence, 2),
            "answer_clarity_score": round(answer_clarity, 2),
            "weights": {
                "emotion_score": 0.30,
                "speech_confidence_score": 0.30,
                "answer_clarity_score": 0.40,
            },
        },
        "coaching_feedback": coaching_feedback,
        "llm_review": {
            "score": llm_score,
            "strengths": llm_review.get("strengths", []),
            "improvements": llm_review.get("improvements", []),
            "suggested_answer": llm_review.get("suggested_answer", ""),
            "communication_feedback": llm_review.get("communication_feedback", ""),
            "linguistic_breakdown": linguistic_breakdown,
            "linguistic_score": round(linguistic_score, 2),
            "answer_clarity_score": round(answer_clarity, 2),
            "answer_quality_score": round(answer_quality_score, 2),
            "optimal_alignment_score": round(optimal_alignment_score, 2),
            "optimal_alignment_feedback": optimal_alignment_feedback,
            "optimal_mismatch_points": optimal_mismatch_points,
        },
    }


@app.post("/analyze-voice-whisper")
@app.post("/analyze-voice-browser-speech")
async def analyze_voice_whisper(
    file: UploadFile = File(...), transcript: str = Form("")
) -> dict:
    file_path = save_upload_file(file, "uploads")
    try:
        from app.whisper_analyzer import analyze_audio, calculate_voice_score

        analysis = await run_in_threadpool(analyze_audio, file_path, transcript)
        voice_score = await run_in_threadpool(calculate_voice_score, analysis)
        return {
            **analysis,
            "voice_score": voice_score,
            "speech_confidence_score": voice_score,
        }
    except Exception:
        return {
            "transcript": "",
            "filler_word_count": 0,
            "words_per_minute": 0.0,
            "speech_rate": 0.0,
            "pause_count": 0,
            "long_pause_count": 0,
            "pause_frequency": 0.0,
            "tone_variation_score": 0.0,
            "clarity_score": 0.0,
            "voice_score": 0.0,
            "speech_confidence_score": 0.0,
            "error": "Voice analyzer unavailable in this environment.",
        }
    finally:
        try:
            os.remove(file_path)
        except Exception:
            pass


@app.post("/analyze-face-frame")
async def analyze_face_frame(
    interview_id: str = Form(...), file: UploadFile = File(...)
) -> dict:
    frame_bytes = await file.read()
    analysis = await run_in_threadpool(
        interview_monitor.analyze_frame_bytes, frame_bytes, interview_id
    )
    attention_score = float((analysis.get("monitor_counts") or {}).get("score", 100))
    coaching_feedback = _build_coaching_feedback(
        filler_count=0,
        attention_score=attention_score,
        speech_rate=120.0,
        long_pause_count=0,
    )
    return {**analysis, "coaching_feedback": coaching_feedback}


@app.post("/analyze-answer-parallel")
async def analyze_answer_parallel(
    interview_id: str = Form(...),
    audio_file: Optional[UploadFile] = File(None),
    frame_file: Optional[UploadFile] = File(None),
    transcript: str = Form(""),
) -> dict:
    """
    Analyze answer in parallel: audio + emotion detection simultaneously.
    This endpoint demonstrates the async parallel pipeline.

    Optional but if provided, runs:
    - Speech-to-text + voice metrics (audio_file)
    - Emotion detection (frame_file)
    ...in parallel using asyncio.gather().

    Args:
        interview_id: Interview session ID
        audio_file: Optional audio file for speech-to-text and voice analysis
        frame_file: Optional video frame for emotion detection
        transcript: Optional pre-transcribed text (fallback)

    Returns:
        Combined analysis with voice metrics, emotion data, and voice_score
    """
    logger.info("Parallel answer analysis started for interview %s", interview_id)

    audio_path = None
    frame_bytes = None

    try:
        # Save audio file if provided
        if audio_file:
            audio_path = save_upload_file(audio_file, "uploads")

        # Read frame if provided
        if frame_file:
            frame_bytes = await frame_file.read()

        # Run parallel pipeline
        if audio_path or frame_bytes:
            result = await process_answer_pipeline(
                audio_path=audio_path or "",
                frame_bytes=frame_bytes or b"",
                interview_id=interview_id,
                fallback_transcript=transcript,
            )

            logger.info(
                "Parallel answer analysis completed for interview %s: all_succeeded=%s, failures=%s",
                interview_id,
                result.get("all_succeeded"),
                result.get("failures"),
            )

            # Return combined result
            return {
                "transcript": result.get("text", ""),
                "filler_word_count": int(
                    result.get("voice", {}).get("filler_word_count", 0)
                ),
                "words_per_minute": float(
                    result.get("voice", {}).get("words_per_minute", 0.0)
                ),
                "speech_rate": float(result.get("voice", {}).get("speech_rate", 0.0)),
                "pause_count": int(result.get("voice", {}).get("pause_count", 0)),
                "long_pause_count": int(
                    result.get("voice", {}).get("long_pause_count", 0)
                ),
                "pause_frequency": float(
                    result.get("voice", {}).get("pause_frequency", 0.0)
                ),
                "tone_variation_score": float(
                    result.get("voice", {}).get("tone_variation_score", 5.0)
                ),
                "clarity_score": float(
                    result.get("voice", {}).get("clarity_score", 5.0)
                ),
                "audio_duration_seconds": float(
                    result.get("voice", {}).get("audio_duration_seconds", 0.0)
                ),
                "voice_score": result.get("voice_score", 5.0),
                "speech_confidence_score": result.get("voice_score", 5.0),
                "emotion_label": result.get("emotion", {}).get(
                    "emotion_label", "neutral"
                ),
                "emotion_score": result.get("emotion", {}).get("emotion_score", 6.0),
                "all_analyses_succeeded": result.get("all_succeeded", False),
                "failed_components": result.get("failures", []),
            }
        else:
            return {"error": "At least one of audio_file or frame_file is required"}

    except Exception as exc:
        logger.error(
            "Parallel answer analysis failed for interview %s: %s", interview_id, exc
        )
        return {
            "error": str(exc),
            "transcript": "",
            "voice_score": 0.0,
            "emotion_score": 6.0,
        }
    finally:
        # Clean up uploaded files
        if audio_path:
            try:
                os.remove(audio_path)
            except Exception:
                pass


@app.get("/monitor-report/{interview_id}")
def monitor_report(interview_id: str) -> dict:
    return interview_monitor.get_report(interview_id)


@app.post("/analytics/session/finalize/{interview_id}")
def finalize_session(interview_id: str, payload: FinalizeSessionRequest) -> dict:
    session_payload = _aggregate_session(
        interview_id=interview_id,
        user_id=payload.user_id,
        fallback_role=payload.role,
    )
    saved = save_session(session_payload)
    return {"session": saved}


@app.get("/analytics/session/{session_id}")
def analytics_session(session_id: str) -> dict:
    session = get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return {"session": session}


@app.get("/analytics/trends")
def analytics_trends(user_id: str = Query("anonymous")) -> dict:
    return get_user_trends(user_id)


@app.post("/peer-review/request")
def peer_review_request(payload: PeerReviewRequestCreate) -> dict:
    try:
        record = create_review_request(payload.model_dump())
        return {"request": record}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/peer-review/submit")
def peer_review_submit(payload: PeerReviewSubmitRequest) -> dict:
    try:
        record = submit_review(payload.model_dump())
        return {"review": record}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/peer-review/close")
def peer_review_close(payload: PeerReviewCloseRequest) -> dict:
    try:
        request_item = close_review_request(payload.session_id, payload.requester_id)
        return {"request": request_item}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/peer-review/{session_id}")
def peer_review_session(session_id: str) -> dict:
    return get_peer_review_session(session_id)
