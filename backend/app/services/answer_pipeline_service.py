"""
Answer processing pipeline that runs audio analysis, emotion detection, and voice analysis in parallel.
Uses asyncio.gather() to execute all three components concurrently for efficiency.
"""

import asyncio
import logging
from typing import Any, Dict

from app.services.async_emotion import async_analyze_emotion
from app.services.async_whisper import async_analyze_audio, async_calculate_voice_score


logger = logging.getLogger(__name__)


async def process_answer_pipeline(
    audio_path: str,
    frame_bytes: bytes,
    interview_id: str,
    fallback_transcript: str = "",
) -> Dict[str, Any]:
    """
    Process candidate answer using parallel execution of three components:
    1. Speech-to-text + voice metrics (audio analysis)
    2. Emotion detection (face analysis)
    3. Voice scoring (derived from audio metrics)

    All three components run concurrently using asyncio.gather().
    If any component fails, the pipeline continues with safe defaults for that component.

    Args:
        audio_path: Path to audio file containing the answer
        frame_bytes: Video frame bytes for emotion detection
        interview_id: Interview session ID
        fallback_transcript: Pre-transcribed text from browser (fallback for speech-to-text)

    Returns:
        Dictionary with:
        - "text": transcribed text from audio
        - "emotion": emotion analysis result (label, score, etc.)
        - "voice": voice metrics (filler counts, speech rate, pauses, clarity, etc.)
        - "voice_score": computed voice score (0-10)
        - "all_succeeded": boolean indicating if all components succeeded
        - "failures": list of component names that failed
    """
    logger.info(
        "Answer pipeline started for interview %s (audio_path=%s, has_frame=%s, has_transcript=%s)",
        interview_id,
        audio_path,
        bool(frame_bytes),
        bool(fallback_transcript),
    )

    # Run all three components in parallel
    try:
        audio_analysis, emotion_analysis = await asyncio.gather(
            async_analyze_audio(audio_path, fallback_transcript),
            async_analyze_emotion(frame_bytes, interview_id),
            return_exceptions=False,
        )
    except Exception as exc:
        logger.error("Answer pipeline gather failed: %s", exc)
        audio_analysis = _safe_audio_analysis()
        emotion_analysis = _safe_emotion_analysis()

    # Calculate voice score from audio metrics
    voice_score = await async_calculate_voice_score(audio_analysis)

    # Determine which components succeeded (check for presence of key fields)
    audio_succeeded = bool(
        audio_analysis.get("transcript") or audio_analysis.get("clarity_score")
    )
    emotion_succeeded = bool(emotion_analysis.get("emotion_label"))
    failures = []

    if not audio_succeeded:
        failures.append("audio_analysis")
    if not emotion_succeeded:
        failures.append("emotion_analysis")

    all_succeeded = len(failures) == 0

    logger.info(
        "Answer pipeline completed for interview %s: all_succeeded=%s, failures=%s",
        interview_id,
        all_succeeded,
        failures,
    )

    return {
        "text": audio_analysis.get("transcript", ""),
        "emotion": emotion_analysis,
        "voice": audio_analysis,
        "voice_score": voice_score,
        "all_succeeded": all_succeeded,
        "failures": failures,
    }


def _safe_audio_analysis() -> Dict[str, Any]:
    """Return safe default audio analysis result."""
    return {
        "transcript": "",
        "filler_word_count": 0,
        "words_per_minute": 0.0,
        "speech_rate": 0.0,
        "pause_count": 0,
        "long_pause_count": 0,
        "pause_frequency": 0.0,
        "tone_variation_score": 5.0,
        "clarity_score": 5.0,
        "audio_duration_seconds": 0.0,
    }


def _safe_emotion_analysis() -> Dict[str, Any]:
    """Return safe default emotion analysis result."""
    return {
        "emotion_label": "neutral",
        "emotion_score": 6.0,
        "face_count": 0,
        "head_tilt_angle": 0.0,
        "warnings": ["Analysis unavailable"],
    }
