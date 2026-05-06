from typing import Any, Dict

from fastapi import APIRouter

from app.models.question_models import (
    QuestionBundle,
    QuestionGenerationRequest,
    QuestionGenerationResponse,
)
from app.services.question_generation_service import (
    generate_questions_async,
    generate_single_question_async,
)
from app.services.role_detection_service import refine_role


router = APIRouter()


# ---------------- QUESTION GENERATION ROUTE ----------------
@router.post(
    "/single",
    summary="Generate 1 role-aligned interview question",
)
async def generate_single_interview_question(
    payload: QuestionGenerationRequest,
) -> Dict[str, Any]:
    refined = refine_role(payload.role, payload.skills)
    question = await generate_single_question_async(
        refined, payload.skills, payload.difficulty
    )
    return {
        "role_input": payload.role,
        "refined_role": refined,
        "difficulty": payload.difficulty,
        "question": question
    }


@router.post(
    "/generate",
    response_model=QuestionGenerationResponse,
    summary="Generate 10 role-aligned interview questions",
    responses={
        200: {
            "description": "Questions generated",
            "content": {
                "application/json": {
                    "example": {
                        "role_input": "Backend Developer",
                        "refined_role": "Backend Software Engineer",
                        "difficulty": "medium",
                        "questions": {
                            "technical": [
                                "[Easy] Explain dependency injection in FastAPI.",
                                "[Easy-Medium] How do you model relational data in PostgreSQL?",
                                "[Medium] How do you debug API latency spikes?",
                                "[Medium-Hard] Design retry + circuit breaker behavior.",
                                "[Hard] Design a globally distributed API.",
                            ],
                            "behavioral": [
                                "Tell me about a difficult production incident.",
                                "How do you prioritize under pressure?",
                                "Describe feedback you received and applied.",
                            ],
                            "scenario": [
                                "A release failed in production. What next?",
                                "How would you handle architectural disagreement?",
                            ],
                        },
                    }
                }
            },
        }
    },
)
async def generate_interview_questions(
    payload: QuestionGenerationRequest,
) -> QuestionGenerationResponse:
    refined = refine_role(payload.role, payload.skills)
    bundle = await generate_questions_async(refined, payload.skills, payload.difficulty)
    return QuestionGenerationResponse(
        role_input=payload.role,
        refined_role=refined,
        difficulty=payload.difficulty,
        questions=QuestionBundle(**bundle),
    )
