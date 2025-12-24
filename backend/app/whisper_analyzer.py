import os
os.environ["PATH"] += r";C:\Users\HYDRA\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg.Essentials_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-8.0.1-essentials_build\bin"

import whisper
import librosa
import re

model = whisper.load_model("base")

FILLER_WORDS = ["uh", "um", "like", "you know", "ah", "er"]

def analyze_audio(audio_path: str):
    result = model.transcribe(audio_path)
    text = result["text"].lower().strip()

    y, sr = librosa.load(audio_path, sr=None)
    duration = librosa.get_duration(y=y, sr=sr)

    words = text.split()
    wpm = (len(words) / duration) * 60 if duration > 0 else 0

    filler_count = sum(len(re.findall(rf"\b{fw}\b", text)) for fw in FILLER_WORDS)

    feedback = []
    if filler_count > 5:
        feedback.append("Too many filler words. Try pausing silently.")
    if wpm < 90:
        feedback.append("Speaking too slowly.")
    elif wpm > 160:
        feedback.append("Speaking too fast.")
    else:
        feedback.append("Good speaking pace.")

    return {
        "transcript": text,
        "filler_word_count": filler_count,
        "words_per_minute": round(wpm, 2),
        "feedback": feedback
    }

def calculate_voice_score(analysis: dict):
    score = 10  # start with full marks

    filler_count = analysis["filler_word_count"]
    wpm = analysis["words_per_minute"]

    if filler_count > 5:
        score -= 3
    elif filler_count > 2:
        score -= 1

    if wpm < 90 or wpm > 160:
        score -= 2

    return max(score, 0)
