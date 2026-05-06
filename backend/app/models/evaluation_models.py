from typing import List, Literal

from pydantic import BaseModel, Field


# ---------------- EVALUATION MODELS ----------------
Difficulty = Literal["easy", "medium", "hard"]


class EvaluationRequest(BaseModel):
    role: str = Field(..., examples=["Backend Developer"])
    question: str = Field(..., examples=["Explain REST vs GraphQL trade-offs."])
    answer: str = Field(
        ...,
        examples=[
            "REST is simple and cache friendly, while GraphQL reduces over-fetching."
        ],
    )
    difficulty: Difficulty = Field(default="medium", examples=["medium"])


class EvaluationResponse(BaseModel):
    score: float = Field(..., ge=0, le=10, examples=[7.4])
    strengths: List[str] = Field(..., examples=[["Clear trade-off analysis"]])
    improvements: List[str] = Field(..., examples=[["Provide concrete examples"]])
    suggested_answer: str = Field(
        ...,
        examples=[
            "A strong answer compares transport, caching, schema evolution, and tooling."
        ],
    )
    communication_feedback: str = Field(
        ..., examples=["Concise, but add structure using bullet points in speech."]
    )
    next_difficulty: Difficulty = Field(..., examples=["hard"])
