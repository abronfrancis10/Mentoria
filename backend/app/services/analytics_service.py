from __future__ import annotations

import os
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from app.services.storage_service import read_json, write_json


ANALYTICS_FILE = os.path.join("uploads", "analytics_sessions.json")
DEFAULT_STORE = {"sessions": []}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _as_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return float(default)


def _as_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except Exception:
        return int(default)


def _safe_str(value: Any, default: str = "") -> str:
    text = str(value or default).strip()
    return text or default


def _load() -> Dict[str, Any]:
    store = read_json(ANALYTICS_FILE, DEFAULT_STORE)
    sessions = store.get("sessions")
    if not isinstance(sessions, list):
        store["sessions"] = []
    return store


def _save(store: Dict[str, Any]) -> None:
    write_json(ANALYTICS_FILE, store)


def _difficulty_ordinal(difficulty: str) -> int:
    norm = _safe_str(difficulty, "medium").lower()
    if norm == "easy":
        return 1
    if norm == "hard":
        return 3
    return 2


def _normalize_session_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
    linguistic_breakdown_raw = payload.get("linguistic_breakdown") or {}
    linguistic_breakdown = {
        "relevance_score": round(
            _as_float(linguistic_breakdown_raw.get("relevance_score"), 0.0), 2
        ),
        "structure_score": round(
            _as_float(linguistic_breakdown_raw.get("structure_score"), 0.0), 2
        ),
        "grammar_score": round(
            _as_float(linguistic_breakdown_raw.get("grammar_score"), 0.0), 2
        ),
        "keyword_match_score": round(
            _as_float(linguistic_breakdown_raw.get("keyword_match_score"), 0.0), 2
        ),
    }
    monitor_report_raw = payload.get("monitor_report") or {}
    coaching_summary_raw = payload.get("coaching_summary") or {}

    return {
        "session_id": _safe_str(payload.get("session_id"), str(uuid.uuid4())),
        "user_id": _safe_str(payload.get("user_id"), "anonymous"),
        "role": _safe_str(payload.get("role"), "General"),
        "started_at": _safe_str(payload.get("started_at"), _now_iso()),
        "completed_at": _safe_str(payload.get("completed_at"), _now_iso()),
        "overall_score": round(_as_float(payload.get("overall_score"), 0.0), 2),
        "overall_interview_score": round(
            _as_float(
                payload.get("overall_interview_score"), payload.get("overall_score")
            ),
            2,
        ),
        "linguistic_score": round(_as_float(payload.get("linguistic_score"), 0.0), 2),
        "answer_quality_score": round(
            _as_float(
                payload.get("answer_quality_score"), payload.get("answer_clarity_score")
            ),
            2,
        ),
        "answer_clarity_score": round(
            _as_float(
                payload.get("answer_clarity_score"), payload.get("answer_quality_score")
            ),
            2,
        ),
        "optimal_alignment_score": round(
            _as_float(payload.get("optimal_alignment_score"), 0.0), 2
        ),
        "emotion_score": round(_as_float(payload.get("emotion_score"), 0.0), 2),
        "text_emotion_score": round(
            _as_float(payload.get("text_emotion_score"), 0.0), 2
        ),
        "face_emotion_score": round(
            _as_float(payload.get("face_emotion_score"), 0.0), 2
        ),
        "attention_score": round(_as_float(payload.get("attention_score"), 0.0), 2),
        "voice_score": round(
            _as_float(
                payload.get("voice_score"), payload.get("speech_confidence_score")
            ),
            2,
        ),
        "speech_confidence_score": round(
            _as_float(
                payload.get("speech_confidence_score"), payload.get("voice_score")
            ),
            2,
        ),
        "filler_word_count": _as_int(payload.get("filler_word_count"), 0),
        "pause_count": _as_int(payload.get("pause_count"), 0),
        "speech_rate": round(_as_float(payload.get("speech_rate"), 0.0), 2),
        "tone_variation_score": round(
            _as_float(payload.get("tone_variation_score"), 0.0), 2
        ),
        "pause_frequency": round(_as_float(payload.get("pause_frequency"), 0.0), 2),
        "clarity_score": round(_as_float(payload.get("clarity_score"), 0.0), 2),
        "linguistic_breakdown": linguistic_breakdown,
        "difficulty_history": list(payload.get("difficulty_history") or []),
        "question_level_history": list(payload.get("question_level_history") or []),
        "difficulty_transition_counts": dict(
            payload.get("difficulty_transition_counts") or {}
        ),
        "final_difficulty_reached": _safe_str(
            payload.get("final_difficulty_reached"), "medium"
        ),
        "monitor_report": {
            "emotion_distribution": dict(
                monitor_report_raw.get("emotion_distribution") or {}
            ),
            "dominant_emotion": _safe_str(
                monitor_report_raw.get("dominant_emotion"), "unknown"
            ),
            "attention_drop_instances": _as_int(
                monitor_report_raw.get("attention_drop_instances"), 0
            ),
            "average_face_visibility_score": round(
                _as_float(monitor_report_raw.get("average_face_visibility_score"), 0.0),
                2,
            ),
            "final_attention_score": round(
                _as_float(monitor_report_raw.get("final_attention_score"), 0.0), 2
            ),
            "emotion_score_percent": round(
                _as_float(monitor_report_raw.get("emotion_score_percent"), 0.0), 2
            ),
            "issue_counts": dict(monitor_report_raw.get("issue_counts") or {}),
            "attention_feedback": dict(
                monitor_report_raw.get("attention_feedback") or {}
            ),
            "emotion_feedback": dict(monitor_report_raw.get("emotion_feedback") or {}),
        },
        "coaching_summary": {
            "total_alerts": _as_int(coaching_summary_raw.get("total_alerts"), 0),
            "alert_counts": dict(coaching_summary_raw.get("alert_counts") or {}),
        },
        "answer_events": list(payload.get("answer_events") or []),
        "timestamp": _safe_str(payload.get("timestamp"), _now_iso()),
    }


def save_session(payload: Dict[str, Any]) -> Dict[str, Any]:
    store = _load()
    sessions: List[Dict[str, Any]] = store["sessions"]
    session = _normalize_session_payload(payload)
    sessions.append(session)
    _save(store)
    return session


def get_session(session_id: str) -> Optional[Dict[str, Any]]:
    store = _load()
    for session in store["sessions"]:
        if _safe_str(session.get("session_id")) == _safe_str(session_id):
            return session
    return None


def get_user_sessions(user_id: str) -> List[Dict[str, Any]]:
    store = _load()
    target = _safe_str(user_id, "anonymous")
    items = [
        s
        for s in store["sessions"]
        if _safe_str(s.get("user_id"), "anonymous") == target
    ]
    return sorted(
        items,
        key=lambda x: _safe_str(x.get("completed_at"), _safe_str(x.get("timestamp"))),
    )


def get_user_trends(user_id: str) -> Dict[str, Any]:
    sessions = get_user_sessions(user_id)
    total = len(sessions)
    if total == 0:
        return {
            "user_id": _safe_str(user_id, "anonymous"),
            "total_sessions": 0,
            "average_score": 0.0,
            "improvement_delta": 0.0,
            "averages": {
                "emotion_score": 0.0,
                "text_emotion_score": 0.0,
                "face_emotion_score": 0.0,
                "voice_score": 0.0,
                "attention_score": 0.0,
                "linguistic_score": 0.0,
                "answer_quality_score": 0.0,
                "answer_clarity_score": 0.0,
                "optimal_alignment_score": 0.0,
                "speech_confidence_score": 0.0,
            },
            "overall_score_trend": [],
            "emotion_score_trend": [],
            "text_emotion_score_trend": [],
            "face_emotion_score_trend": [],
            "attention_score_trend": [],
            "voice_score_trend": [],
            "speech_confidence_score_trend": [],
            "answer_quality_score_trend": [],
            "answer_clarity_score_trend": [],
            "optimal_alignment_score_trend": [],
            "difficulty_progression_trend": [],
            "linguistic_subscore_trends": {
                "relevance_score": [],
                "structure_score": [],
                "grammar_score": [],
                "keyword_match_score": [],
            },
            "sessions": [],
        }

    overall_values = [_as_float(s.get("overall_score")) for s in sessions]
    emotion_values = [_as_float(s.get("emotion_score")) for s in sessions]
    text_emotion_values = [_as_float(s.get("text_emotion_score")) for s in sessions]
    face_emotion_values = [_as_float(s.get("face_emotion_score")) for s in sessions]
    voice_values = [_as_float(s.get("voice_score")) for s in sessions]
    attention_values = [_as_float(s.get("attention_score")) for s in sessions]
    linguistic_values = [_as_float(s.get("linguistic_score")) for s in sessions]
    answer_quality_values = [_as_float(s.get("answer_quality_score")) for s in sessions]
    answer_clarity_values = [
        _as_float(
            s.get("answer_clarity_score"), _as_float(s.get("answer_quality_score"))
        )
        for s in sessions
    ]
    optimal_alignment_values = [
        _as_float(s.get("optimal_alignment_score")) for s in sessions
    ]
    speech_confidence_values = [
        _as_float(s.get("speech_confidence_score"), _as_float(s.get("voice_score")))
        for s in sessions
    ]
    improvement_delta = (
        round(overall_values[-1] - overall_values[0], 2) if total > 1 else 0.0
    )

    def trend_for(key: str) -> List[Dict[str, Any]]:
        trend = []
        for idx, session in enumerate(sessions):
            trend.append(
                {
                    "session_index": idx + 1,
                    "session_id": _safe_str(session.get("session_id")),
                    "value": round(_as_float(session.get(key), 0.0), 2),
                    "timestamp": _safe_str(
                        session.get("completed_at"), _safe_str(session.get("timestamp"))
                    ),
                }
            )
        return trend

    def linguistic_trend_for(subkey: str) -> List[Dict[str, Any]]:
        trend = []
        for idx, session in enumerate(sessions):
            breakdown = session.get("linguistic_breakdown") or {}
            trend.append(
                {
                    "session_index": idx + 1,
                    "session_id": _safe_str(session.get("session_id")),
                    "value": round(_as_float(breakdown.get(subkey), 0.0), 2),
                    "timestamp": _safe_str(
                        session.get("completed_at"), _safe_str(session.get("timestamp"))
                    ),
                }
            )
        return trend

    difficulty_progression_trend = []
    for idx, session in enumerate(sessions):
        final_difficulty = _safe_str(session.get("final_difficulty_reached"), "medium")
        difficulty_progression_trend.append(
            {
                "session_index": idx + 1,
                "session_id": _safe_str(session.get("session_id")),
                "difficulty": final_difficulty,
                "ordinal": _difficulty_ordinal(final_difficulty),
                "timestamp": _safe_str(
                    session.get("completed_at"), _safe_str(session.get("timestamp"))
                ),
            }
        )

    return {
        "user_id": _safe_str(user_id, "anonymous"),
        "total_sessions": total,
        "average_score": round(sum(overall_values) / total, 2),
        "improvement_delta": improvement_delta,
        "averages": {
            "emotion_score": round(sum(emotion_values) / total, 2),
            "text_emotion_score": round(sum(text_emotion_values) / total, 2),
            "face_emotion_score": round(sum(face_emotion_values) / total, 2),
            "voice_score": round(sum(voice_values) / total, 2),
            "attention_score": round(sum(attention_values) / total, 2),
            "linguistic_score": round(sum(linguistic_values) / total, 2),
            "answer_quality_score": round(sum(answer_quality_values) / total, 2),
            "answer_clarity_score": round(sum(answer_clarity_values) / total, 2),
            "optimal_alignment_score": round(sum(optimal_alignment_values) / total, 2),
            "speech_confidence_score": round(sum(speech_confidence_values) / total, 2),
        },
        "overall_score_trend": trend_for("overall_score"),
        "emotion_score_trend": trend_for("emotion_score"),
        "text_emotion_score_trend": trend_for("text_emotion_score"),
        "face_emotion_score_trend": trend_for("face_emotion_score"),
        "attention_score_trend": trend_for("attention_score"),
        "voice_score_trend": trend_for("voice_score"),
        "speech_confidence_score_trend": trend_for("speech_confidence_score"),
        "answer_quality_score_trend": trend_for("answer_quality_score"),
        "answer_clarity_score_trend": trend_for("answer_clarity_score"),
        "optimal_alignment_score_trend": trend_for("optimal_alignment_score"),
        "difficulty_progression_trend": difficulty_progression_trend,
        "linguistic_subscore_trends": {
            "relevance_score": linguistic_trend_for("relevance_score"),
            "structure_score": linguistic_trend_for("structure_score"),
            "grammar_score": linguistic_trend_for("grammar_score"),
            "keyword_match_score": linguistic_trend_for("keyword_match_score"),
        },
        "sessions": sessions,
    }
