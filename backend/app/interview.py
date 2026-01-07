from fastapi import APIRouter, UploadFile, File
from pydantic import BaseModel
import uuid
import random

router = APIRouter()

# -----------------------
# In-memory storage
# -----------------------
SESSIONS = {}

QUESTIONS = {
    "easy": [
        "Tell me about yourself.",
        "What are your strengths?",
    ],
    "medium": [
        "Explain a challenging project you worked on.",
        "How do you handle tight deadlines?",
    ],
    "hard": [
        "Describe a situation where you failed and what you learned.",
        "How would you handle conflict in a team?",
    ],
}

# -----------------------
# Request models
# -----------------------
class StartInterviewRequest(BaseModel):
    role: str
    type: str

class AnswerRequest(BaseModel):
    answer: str


# -----------------------
# Helpers
# -----------------------
def next_difficulty(current, score):
    if score >= 8:
        return "hard" if current == "medium" else current
    if score <= 4:
        return "easy" if current == "medium" else current
    return current


def evaluate_answer(answer: str):
    length = len(answer.split())
    if length > 80:
        return 9
    if length > 40:
        return 7
    if length > 20:
        return 5
    return 3


# -----------------------
# Routes
# -----------------------
@router.post("/start")
def start_interview(payload: StartInterviewRequest):
    interview_id = str(uuid.uuid4())

    difficulty = "medium"
    question = random.choice(QUESTIONS[difficulty])

    SESSIONS[interview_id] = {
        "difficulty": difficulty,
        "question": question,
    }

    return {
        "interview_id": interview_id,
        "first_question": question,
    }


@router.post("/{interview_id}/answer")
def submit_text_answer(interview_id: str, payload: AnswerRequest):
    session = SESSIONS.get(interview_id)
    if not session:
        return {"error": "Invalid interview ID"}

    score = evaluate_answer(payload.answer)
    new_difficulty = next_difficulty(session["difficulty"], score)
    next_question = random.choice(QUESTIONS[new_difficulty])

    session["difficulty"] = new_difficulty
    session["question"] = next_question

    return {
        "transcript": payload.answer,
        "score": score,
        "next_question": next_question,
    }


@router.post("/{interview_id}/answer/audio")
async def submit_audio_answer(
    interview_id: str,
    audio: UploadFile = File(...),
    snapshot: UploadFile | None = File(None),
):
    session = SESSIONS.get(interview_id)
    if not session:
        return {"error": "Invalid interview ID"}

    # Fake transcript for now
    transcript = "This is a transcribed audio answer."

    score = random.randint(4, 9)
    new_difficulty = next_difficulty(session["difficulty"], score)
    next_question = random.choice(QUESTIONS[new_difficulty])

    session["difficulty"] = new_difficulty
    session["question"] = next_question

    return {
        "transcript": transcript,
        "score": score,
        "next_question": next_question,
    }
