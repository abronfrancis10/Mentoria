from fastapi import APIRouter

from app.models.evaluation_models import EvaluationRequest, EvaluationResponse
from app.services.response_evaluation_service import (
    evaluate_response_async,
)


router = APIRouter()


# ---------------- RESPONSE EVALUATION ROUTE ----------------
@router.post(
    "/evaluate",
    response_model=EvaluationResponse,
    summary="Evaluate a candidate answer and update adaptive difficulty",
    responses={
        200: {
            "description": "Answer evaluated",
            "content": {
                "application/json": {
                    "example": {
                        "score": 7.8,
                        "strengths": [
                            "Clear structure",
                            "Good trade-off analysis",
                        ],
                        "improvements": [
                            "Add one production-scale example",
                        ],
                        "suggested_answer": "A stronger answer starts with definition, trade-offs, and real metrics.",
                        "communication_feedback": "Maintain concise structure and reduce filler words.",
                        "next_difficulty": "hard",
                    }
                }
            },
        }
    },
)
async def evaluate_candidate_answer(payload: EvaluationRequest) -> EvaluationResponse:
    result = await evaluate_response_async(
        role=payload.role,
        question=payload.question,
        answer=payload.answer,
        difficulty=payload.difficulty,
    )
    return EvaluationResponse(**result)
