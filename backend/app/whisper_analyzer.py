import whisper
import librosa
import re
import os

# FIX FFmpeg PATH (important on Windows)
os.environ["PATH"] += r";C:\Users\HYDRA\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg.Essentials_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-8.0.1-essentials_build\bin"

model = whisper.load_model("base")
FILLERS = ["uh", "um", "like", "you know", "ah", "er"]

def analyze_audio(audio_path):
    result = model.transcribe(audio_path)
    text = result["text"].lower()

    y, sr = librosa.load(audio_path, sr=None)
    duration = librosa.get_duration(y=y, sr=sr)

    words = text.split()
    wpm = (len(words) / duration) * 60 if duration > 0 else 0
    filler_count = sum(len(re.findall(rf"\b{f}\b", text)) for f in FILLERS)

    return {
        "transcript": text,
        "filler_word_count": filler_count,
        "words_per_minute": round(wpm, 2)
    }

def calculate_voice_score(analysis):
    score = 10
    if analysis["filler_word_count"] > 3:
        score -= 2
    if analysis["words_per_minute"] < 90 or analysis["words_per_minute"] > 160:
        score -= 2
    return max(score, 0)
import whisper
import librosa
import re
import os

# FIX FFmpeg PATH (important on Windows)
os.environ["PATH"] += r";C:\Users\HYDRA\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg.Essentials_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-8.0.1-essentials_build\bin"

model = whisper.load_model("base")
FILLERS = ["uh", "um", "like", "you know", "ah", "er"]

def analyze_audio(audio_path):
    result = model.transcribe(audio_path)
    text = result["text"].lower()

    y, sr = librosa.load(audio_path, sr=None)
    duration = librosa.get_duration(y=y, sr=sr)

    words = text.split()
    wpm = (len(words) / duration) * 60 if duration > 0 else 0
    filler_count = sum(len(re.findall(rf"\b{f}\b", text)) for f in FILLERS)

    return {
        "transcript": text,
        "filler_word_count": filler_count,
        "words_per_minute": round(wpm, 2)
    }

def calculate_voice_score(analysis):
    score = 10
    if analysis["filler_word_count"] > 3:
        score -= 2
    if analysis["words_per_minute"] < 90 or analysis["words_per_minute"] > 160:
        score -= 2
    return max(score, 0)
