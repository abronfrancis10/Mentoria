"""
Async wrapper for emotion detection (face analysis).
Converts blocking computer vision operations to non-blocking async operations using ThreadPoolExecutor.
"""

import asyncio
import logging
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Dict

from app.ai_interview_monitor import monitor as interview_monitor


logger = logging.getLogger(__name__)
_executor = ThreadPoolExecutor(max_workers=2)


async def async_analyze_emotion(
    frame_bytes: bytes, interview_id: str
) -> Dict[str, Any]:
    """
    Async wrapper for emotion detection from face frame.

    Args:
        frame_bytes: Raw frame data (bytes)
        interview_id: Interview session ID for state tracking

    Returns:
        Dictionary with emotion_label, emotion_score, face_count, warnings, etc.
    """
    loop = asyncio.get_event_loop()
    try:
        result = await loop.run_in_executor(
            _executor,
            lambda: interview_monitor.analyze_frame_bytes(frame_bytes, interview_id),
        )
        logger.debug("Emotion analysis succeeded for interview %s", interview_id)
        return result if isinstance(result, dict) else _safe_emotion_result()
    except asyncio.TimeoutError:
        logger.warning("async_analyze_emotion timed out for interview %s", interview_id)
        return _safe_emotion_result()
    except Exception as exc:
        logger.warning(
            "async_analyze_emotion failed for interview %s: %s", interview_id, exc
        )
        return _safe_emotion_result()


def _safe_emotion_result() -> Dict[str, Any]:
    """
    Return safe default emotion result when analysis fails.
    """
    return {
        "emotion_label": "neutral",
        "emotion_score": 6.0,
        "face_count": 0,
        "head_tilt_angle": 0.0,
        "warnings": ["Emotion analysis unavailable"],
        "vision_available": False,
        "deepface_available": False,
        "mediapipe_available": False,
    }
