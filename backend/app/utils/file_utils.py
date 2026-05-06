import os
import re
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from fastapi import HTTPException, UploadFile


ALLOWED_EXTENSIONS = {".pdf", ".docx"}


# ---------------- FILE HELPERS ----------------
def ensure_directory(path: str) -> None:
    Path(path).mkdir(parents=True, exist_ok=True)


def sanitize_filename(filename: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9._-]", "_", filename or "resume")
    return cleaned[:255]


def validate_resume_file(upload_file: UploadFile) -> str:
    extension = Path(upload_file.filename or "").suffix.lower()
    if extension not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail="Invalid file type. Only PDF and DOCX are supported.",
        )
    return extension


def save_upload_file(upload_file: UploadFile, upload_dir: str) -> str:
    ensure_directory(upload_dir)
    safe_name = sanitize_filename(upload_file.filename or "resume")
    path_obj = Path(safe_name)
    stem = path_obj.stem or "file"
    suffix = path_obj.suffix
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S%f")
    unique_name = f"{stem}_{timestamp}_{uuid4().hex[:8]}{suffix}"
    file_path = os.path.join(upload_dir, unique_name)
    with open(file_path, "wb") as f:
        f.write(upload_file.file.read())
    return file_path
