"""
Async wrappers for audio analysis (speech-to-text and voice metrics).
Converts blocking librosa/whisper operations to non-blocking async operations using ThreadPoolExecutor.
"""

import asyncio
import logging
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Dict

from app.whisper_analyzer import analyze_audio, calculate_voice_score


logger = logging.getLogger(__name__)
_executor = ThreadPoolExecutor(max_workers=2)


async def async_analyze_audio(
    audio_path: str,
    transcript_text: str = "",
) -> Dict[str, Any]:
    """
    Async wrapper for audio analysis (speech-to-text + voice metrics).

    Args:
        audio_path: Path to audio file
        transcript_text: Optional pre-transcribed text (fallback from browser)

    Returns:
        Dictionary with transcript, filler counts, speech rate, pauses, tone, clarity scores
    """
    loop = asyncio.get_event_loop()
    try:
        result = await loop.run_in_executor(
            _executor, lambda: analyze_audio(audio_path, transcript_text)
        )
        logger.debug("Audio analysis succeeded for %s", audio_path)
        return result if isinstance(result, dict) else {}
    except asyncio.TimeoutError:
        logger.warning("async_analyze_audio timed out for %s", audio_path)
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
    except Exception as exc:
        logger.warning("async_analyze_audio failed: %s", exc)
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


async def async_calculate_voice_score(analysis: Dict[str, Any]) -> float:
    """
    Async wrapper for voice score calculation.

    Args:
        analysis: Dictionary from async_analyze_audio

    Returns:
        Voice score (0-10)
    """
    loop = asyncio.get_event_loop()
    try:
        result = await loop.run_in_executor(
            _executor, lambda: calculate_voice_score(analysis)
        )
        return float(result) if result is not None else 5.0
    except Exception as exc:
        logger.warning("async_calculate_voice_score failed: %s", exc)
        return 5.0
