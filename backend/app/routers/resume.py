from fastapi import APIRouter, File, Form, UploadFile

from app.models.resume_models import ResumeUploadResponse
from app.services.resume_parser_service import parse_resume
from app.services.role_detection_service import refine_role
from app.utils.file_utils import save_upload_file, validate_resume_file


router = APIRouter()
UPLOAD_DIR = "uploads"


# ---------------- RESUME UPLOAD ROUTE ----------------
@router.post(
    "/upload",
    response_model=ResumeUploadResponse,
    summary="Upload resume and extract skills",
    responses={
        200: {
            "description": "Resume parsed successfully",
            "content": {
                "application/json": {
                    "example": {
                        "filename": "resume.pdf",
                        "role_input": "Software Engineer",
                        "refined_role": "Backend Software Engineer",
                        "skills": ["python", "fastapi", "sql"],
                        "extracted_text_preview": "Experienced engineer...",
                    }
                }
            },
        }
    },
)
async def upload_resume(
    role: str = Form(..., description="Candidate target role"),
    resume: UploadFile = File(..., description="Resume file (.pdf or .docx)"),
) -> ResumeUploadResponse:
    extension = validate_resume_file(resume)
    path = save_upload_file(resume, UPLOAD_DIR)
    text, skills = parse_resume(path, extension)
    refined = refine_role(role, skills)
    return ResumeUploadResponse(
        filename=resume.filename or "resume",
        role_input=role,
        refined_role=refined,
        skills=skills,
        extracted_text_preview=text[:600],
    )
