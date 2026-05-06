import os
import re
from threading import Lock
from typing import Dict

import librosa
import numpy as np


os.environ["PATH"] += (
    r";C:\Users\HYDRA\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg.Essentials_"
    r"Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-8.0.1-essentials_build\bin"
)

FILLERS = ["uh", "um", "like", "you know", "ah", "er"]
_WHISPER_MODEL = None
_WHISPER_LOCK = Lock()
_WHISPER_LOAD_FAILED = False


def _load_whisper_model():
    global _WHISPER_MODEL, _WHISPER_LOAD_FAILED
    if _WHISPER_MODEL is not None:
        return _WHISPER_MODEL
    if _WHISPER_LOAD_FAILED:
        return None

    with _WHISPER_LOCK:
        if _WHISPER_MODEL is not None:
            return _WHISPER_MODEL
        if _WHISPER_LOAD_FAILED:
            return None
        try:
            import whisper  # type: ignore

            model_name = os.getenv("MENTORIA_WHISPER_MODEL", "base").strip() or "base"
            _WHISPER_MODEL = whisper.load_model(model_name)
            return _WHISPER_MODEL
        except Exception:
            _WHISPER_LOAD_FAILED = True
            return None


def _transcribe_with_whisper(audio_path: str) -> str:
    model = _load_whisper_model()
    if model is None:
        return ""
    try:
        result = model.transcribe(audio_path, fp16=False, language="en")
        return str(result.get("text", "")).strip()
    except Exception:
        return ""


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def _pause_metrics(y: np.ndarray, sr: int, duration: float) -> Dict[str, float]:
    frame_length = 2048
    hop_length = 512
    rms = librosa.feature.rms(y=y, frame_length=frame_length, hop_length=hop_length)[0]
    if len(rms) == 0:
        return {"pause_count": 0, "long_pause_count": 0, "pause_frequency": 0.0}

    threshold = max(0.01, float(np.median(rms) * 0.35))
    silence = rms < threshold
    pause_count = 0
    long_pause_count = 0
    run = 0
    for is_silent in silence:
        if is_silent:
            run += 1
            continue
        if run > 0:
            pause_duration = (run * hop_length) / float(sr)
            if pause_duration >= 0.35:
                pause_count += 1
            if pause_duration >= 1.2:
                long_pause_count += 1
            run = 0
    if run > 0:
        pause_duration = (run * hop_length) / float(sr)
        if pause_duration >= 0.35:
            pause_count += 1
        if pause_duration >= 1.2:
            long_pause_count += 1

    minutes = duration / 60.0 if duration > 0 else 0.0
    pause_frequency = (pause_count / minutes) if minutes > 0 else 0.0
    return {
        "pause_count": int(pause_count),
        "long_pause_count": int(long_pause_count),
        "pause_frequency": round(float(pause_frequency), 2),
    }


def _tone_variation_score(y: np.ndarray, sr: int) -> float:
    centroid = librosa.feature.spectral_centroid(y=y, sr=sr)[0]
    if len(centroid) == 0:
        return 5.0
    mean = float(np.mean(centroid)) or 1.0
    std = float(np.std(centroid))
    ratio = std / mean
    score = _clamp(3.0 + ratio * 30.0, 0.0, 10.0)
    return round(score, 2)


def _clarity_score(
    filler_count: int,
    speech_rate: float,
    pause_frequency: float,
    tone_variation_score: float,
) -> float:
    score = 10.0
    if filler_count >= 3:
        score -= min(3.0, filler_count * 0.4)
    if speech_rate < 90:
        score -= 2.0
    elif speech_rate > 160:
        score -= 2.0
    if pause_frequency > 10:
        score -= 1.5
    elif pause_frequency > 6:
        score -= 1.0
    if tone_variation_score < 4.0:
        score -= 1.0
    return round(_clamp(score, 0.0, 10.0), 2)


def analyze_audio(
    audio_path: str, transcript_text: str = ""
) -> Dict[str, float | str | int]:
    raw_text = str(transcript_text or "").strip()
    if not raw_text:
        # Browser transcript is preferred for latency; Whisper is fallback for missing transcript.
        raw_text = _transcribe_with_whisper(audio_path)
    text = raw_text.lower()

    y, sr = librosa.load(audio_path, sr=None)
    duration = float(librosa.get_duration(y=y, sr=sr))

    words = text.split()
    wpm = (len(words) / duration) * 60 if duration > 0 else 0.0
    filler_count = sum(len(re.findall(rf"\b{f}\b", text)) for f in FILLERS)

    pauses = _pause_metrics(y, sr, duration)
    tone_score = _tone_variation_score(y, sr)
    clarity = _clarity_score(
        filler_count=filler_count,
        speech_rate=wpm,
        pause_frequency=float(pauses["pause_frequency"]),
        tone_variation_score=tone_score,
    )

    return {
        "transcript": raw_text,
        "filler_word_count": int(filler_count),
        "words_per_minute": round(float(wpm), 2),
        "speech_rate": round(float(wpm), 2),
        "pause_count": int(pauses["pause_count"]),
        "long_pause_count": int(pauses["long_pause_count"]),
        "pause_frequency": float(pauses["pause_frequency"]),
        "tone_variation_score": float(tone_score),
        "clarity_score": float(clarity),
        "audio_duration_seconds": round(duration, 2),
    }


def calculate_voice_score(analysis: Dict[str, float | str | int]) -> float:
    filler = int(analysis.get("filler_word_count", 0) or 0)
    speech_rate = float(
        analysis.get("speech_rate", analysis.get("words_per_minute", 0.0)) or 0.0
    )
    long_pauses = int(analysis.get("long_pause_count", 0) or 0)
    clarity_score = float(analysis.get("clarity_score", 7.0) or 7.0)
    tone_score = float(analysis.get("tone_variation_score", 5.0) or 5.0)

    score = 10.0
    if filler >= 3:
        score -= min(2.5, filler * 0.35)
    if speech_rate < 90 or speech_rate > 160:
        score -= 2.0
    if long_pauses >= 2:
        score -= 1.5
    score = (score * 0.45) + (clarity_score * 0.35) + (tone_score * 0.20)
    return round(_clamp(score, 0.0, 10.0), 2)
