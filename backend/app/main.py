import shutil
import os
from fastapi import FastAPI, UploadFile, File
from pydantic import BaseModel
from typing import List

from .resume_parser import parse_resume
from .role_detector import detect_role
from .skill_weighting import weight_skills
from .question_generator import generate_questions
from .answer_evaluator import evaluate_answer
from .interview_engine import (
    create_interview,
    get_current_question,
    submit_answer,
    is_interview_complete,
    get_summary
)
from .whisper_analyzer import analyze_audio

from .final_scorer import calculate_final_score
from .whisper_analyzer import calculate_voice_score


app = FastAPI(
    title="Mentoria API",
    description="Backend for AI Mock Interview Platform",
    version="1.0.0"
)

UPLOAD_DIR = "uploads"

if not os.path.exists(UPLOAD_DIR):
    os.mkdir(UPLOAD_DIR)


@app.get("/")
def root():
    return {"message": "Mentoria backend is running"}

@app.post("/parse-resume")
async def parse_uploaded_resume(file: UploadFile = File(...)):
    file_path = os.path.join(UPLOAD_DIR, file.filename)

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    parsed_data = parse_resume(file_path)
    role_data = detect_role(parsed_data["skills"])
    skill_weights = weight_skills(
    role_data["detected_role"],
    parsed_data["skills"]
    )
    questions = generate_questions(
    skill_weights["core_skills"],
    skill_weights["secondary_skills"]
    )


    return {
    "filename": file.filename,
    "parsed_data": parsed_data,
    "role_detection": role_data,
    "skill_weighting": skill_weights,
    "generated_questions": questions
}

@app.post("/evaluate-answer")
async def evaluate_user_answer(question: str, answer: str):
    evaluation = evaluate_answer(question, answer)

    return {
        "question": question,
        "answer": answer,
        "evaluation": evaluation
    }

#Interview Module
class InterviewRequest(BaseModel):
    questions: List[str]


class AnswerRequest(BaseModel):
    question: str
    answer: str

@app.post("/start-interview", response_model=dict)
async def start_interview(request: InterviewRequest):
    interview_id = create_interview(request.questions)
    return {
        "interview_id": interview_id,
        "message": "Interview started"
    }


@app.get("/next-question/{interview_id}")
async def next_question(interview_id: str):
    question = get_current_question(interview_id)

    if question is None:
        return {"message": "Interview complete"}

    return {"question": question}


@app.post("/submit-answer/{interview_id}")
async def submit_interview_answer(
    interview_id: str,
    request: AnswerRequest
):
    evaluation = evaluate_answer(request.question, request.answer)
    submit_answer(interview_id, evaluation)

    if is_interview_complete(interview_id):
        return {
            "message": "Interview completed",
            "summary": get_summary(interview_id)
        }

    return {
        "message": "Answer submitted",
        "evaluation": evaluation
    }


@app.post("/analyze-voice-whisper")
async def analyze_voice_whisper(file: UploadFile = File(...)):
    audio_path = f"uploads/{file.filename}"

    with open(audio_path, "wb") as f:
        f.write(await file.read())

    analysis = analyze_audio(audio_path)

    return analysis

@app.post("/final-evaluation")
async def final_evaluation(
    question: str,
    answer: str,
    file: UploadFile = File(...)
):
    # Save audio
    audio_path = f"uploads/{file.filename}"
    with open(audio_path, "wb") as f:
        f.write(await file.read())

    # Text answer evaluation
    answer_eval = evaluate_answer(question, answer)
    answer_score = answer_eval["score"]

    # Voice analysis
    voice_analysis = analyze_audio(audio_path)
    voice_score = calculate_voice_score(voice_analysis)

    # Final combined score
    final_result = calculate_final_score(answer_score, voice_score)

    return {
        "question": question,
        "answer": answer,
        "answer_evaluation": answer_eval,
        "voice_analysis": voice_analysis,
        "voice_score": voice_score,
        "final_result": final_result
    }
