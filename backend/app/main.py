from fastapi import FastAPI, UploadFile, File,Form
from pydantic import BaseModel

from app.mistral_questions import generate_questions_with_answers
from app.interview_engine import (
    create_interview,
    get_next_question,
    store_answer,
    interviews
)
from app.optimality_checker import calculate_optimality_score
from app.answer_evaluator import evaluate_answer
from app.final_scorer import calculate_final_score

app = FastAPI()

@app.get("/")
def health():
    return {"status": "ok"}

class TextAnswerRequest(BaseModel):
    answer: str

@app.post("/start-interview")
async def start_interview(
    role: str = Form(...),
    resume: UploadFile = File(...)
):
    resume_text = (await resume.read()).decode("utf-8", errors="ignore")

    questions = generate_questions_with_answers(role, resume_text)
    interview_id = create_interview(questions)

    return {"interview_id": interview_id}

@app.get("/next-question/{interview_id}")
def next_question(interview_id: str):
    return get_next_question(interview_id)

@app.post("/submit-answer/{interview_id}")
def submit_answer(interview_id: str, payload: TextAnswerRequest):
    transcript = payload.answer

    store_answer(interview_id, transcript)

    optimal = interviews[interview_id]["answers"][-1]["optimal_answer"]

    optimality = calculate_optimality_score(transcript, optimal)
    quality = evaluate_answer(transcript)
    voice_score = 7  # text mode

    final_score, feedback = calculate_final_score(
        optimality, quality, voice_score
    )

    return {
        "final_score": final_score,
        "feedback": feedback
    }

@app.get("/final-feedback/{interview_id}")
def final_feedback(interview_id: str):
    answers = interviews[interview_id]["answers"]

    combined_text = "\n".join(
        f"Q: {a['question']}\nA: {a['candidate_answer']}"
        for a in answers
    )

    # Later: send combined_text to Mistral for final feedback
    return {
        "total_questions": len(answers),
        "summary": "Final feedback generated here"
    }
