from typing import List

from pydantic import BaseModel, Field


# ---------------- RESUME RESPONSE MODELS ----------------
class ResumeUploadResponse(BaseModel):
    filename: str = Field(..., examples=["resume.pdf"])
    role_input: str = Field(..., examples=["Software Engineer"])
    refined_role: str = Field(..., examples=["Backend Software Engineer"])
    skills: List[str] = Field(..., examples=[["python", "fastapi", "sql"]])
    extracted_text_preview: str = Field(
        ..., examples=["Experienced software engineer with Python and FastAPI..."]
    )
