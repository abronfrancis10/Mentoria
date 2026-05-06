from __future__ import annotations

from typing import Optional


def clamp_score(value: float, low: float = 0.0, high: float = 10.0) -> float:
    return max(low, min(high, float(value)))


def normalize_score(value: Optional[float], fallback: float = 0.0) -> float:
    try:
        score = float(value if value is not None else fallback)
    except Exception:
        score = float(fallback)
    if score > 10.0:
        score = score / 10.0
    return round(clamp_score(score), 2)


def emotion_score_from_label(label: str) -> float:
    normalized = (label or "").lower().strip()
    if normalized in {"happy", "neutral", "positive"}:
        return 9.0
    if normalized == "surprise":
        return 7.0
    if normalized in {"sad", "angry", "fear", "disgust", "negative"}:
        return 3.0
    return 6.0


def combine_emotion_scores(
    face_emotion_score: float,
    text_emotion_score: float,
    has_face_emotion: bool = True,
    face_weight: float = 0.6,
) -> float:
    text_score = normalize_score(text_emotion_score, 6.0)
    if not has_face_emotion:
        return text_score

    face_score = normalize_score(face_emotion_score, 0.0)
    blend = (face_weight * face_score) + ((1.0 - face_weight) * text_score)
    return round(clamp_score(blend), 2)


def speech_confidence_score(
    provided_voice_score: Optional[float],
    filler_word_count: int,
    speech_rate: float,
    long_pause_count: int,
    pause_frequency: float,
    tone_variation_score: float,
    clarity_score: float,
) -> float:
    base = 10.0
    if filler_word_count >= 3:
        base -= min(2.6, filler_word_count * 0.35)
    if speech_rate < 90 or speech_rate > 160:
        base -= 1.8
    if long_pause_count >= 2:
        base -= 1.6
    if pause_frequency > 10:
        base -= 1.2
    elif pause_frequency > 6:
        base -= 0.8

    metric_score = (
        (0.50 * clamp_score(base))
        + (0.25 * normalize_score(clarity_score, 7.0))
        + (0.25 * normalize_score(tone_variation_score, 5.0))
    )

    normalized_provided = normalize_score(provided_voice_score, 0.0)
    if normalized_provided > 0:
        return round(clamp_score((0.6 * normalized_provided) + (0.4 * metric_score)), 2)
    return round(clamp_score(metric_score), 2)


def answer_clarity_score(
    relevance_score: float,
    structure_score: float,
    grammar_score: float,
    keyword_match_score: float,
    fallback_linguistic_score: float = 0.0,
) -> float:
    weighted = (
        (0.30 * normalize_score(relevance_score, 0.0))
        + (0.25 * normalize_score(structure_score, 0.0))
        + (0.25 * normalize_score(grammar_score, 0.0))
        + (0.20 * normalize_score(keyword_match_score, 0.0))
    )
    if weighted <= 0 and fallback_linguistic_score > 0:
        return normalize_score(fallback_linguistic_score, 0.0)
    return round(clamp_score(weighted), 2)


def final_interview_score(
    emotion_score: float,
    speech_confidence: float,
    answer_clarity: float,
    emotion_weight: float = 0.30,
    speech_weight: float = 0.30,
    clarity_weight: float = 0.40,
) -> float:
    total = emotion_weight + speech_weight + clarity_weight
    if total <= 0:
        total = 1.0

    normalized = (
        (emotion_weight / total) * normalize_score(emotion_score, 0.0)
        + (speech_weight / total) * normalize_score(speech_confidence, 0.0)
        + (clarity_weight / total) * normalize_score(answer_clarity, 0.0)
    )
    return round(clamp_score(normalized), 2)
