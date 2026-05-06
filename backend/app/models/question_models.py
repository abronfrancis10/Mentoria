from typing import List, Literal

from pydantic import BaseModel, Field


# ---------------- QUESTION MODELS ----------------
Difficulty = Literal["easy", "medium", "hard"]


class QuestionGenerationRequest(BaseModel):
    role: str = Field(..., examples=["Backend Developer"])
    skills: List[str] = Field(..., examples=[["python", "fastapi", "postgresql"]])
    difficulty: Difficulty = Field(default="medium", examples=["medium"])


class QuestionBundle(BaseModel):
    technical: List[str] = Field(
        ...,
        examples=[
            [
                "Explain dependency injection in FastAPI.",
                "How do you optimize SQL queries for large datasets?",
            ]
        ],
    )
    behavioral: List[str] = Field(
        ...,
        examples=[["Tell me about a time you handled a production incident."]],
    )
    scenario: List[str] = Field(
        ...,
        examples=[["How would you design a resilient interview scoring API?"]],
    )


class QuestionGenerationResponse(BaseModel):
    role_input: str = Field(..., examples=["Backend Developer"])
    refined_role: str = Field(..., examples=["Backend Software Engineer"])
    difficulty: Difficulty = Field(..., examples=["medium"])
    questions: QuestionBundle
