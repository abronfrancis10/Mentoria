import re
import zipfile
from typing import List, Tuple
from xml.etree import ElementTree as ET


SKILLS_DB = {
    "python",
    "java",
    "c++",
    "sql",
    "javascript",
    "typescript",
    "react",
    "node",
    "fastapi",
    "django",
    "flask",
    "docker",
    "kubernetes",
    "aws",
    "azure",
    "gcp",
    "machine learning",
    "data analysis",
    "nlp",
    "html",
    "css",
    "postgresql",
    "mongodb",
    "redis",
    "git",
}


# ---------------- TEXT EXTRACTION ----------------
def _extract_text_from_pdf(file_path: str) -> str:
    try:
        import pdfplumber  # type: ignore
    except Exception as exc:
        raise RuntimeError("pdfplumber is required for PDF parsing.") from exc

    text_parts: List[str] = []
    with pdfplumber.open(file_path) as pdf:
        for page in pdf.pages:
            text_parts.append(page.extract_text() or "")
    return "\n".join(text_parts)


def _extract_text_from_docx(file_path: str) -> str:
    try:
        from docx import Document  # type: ignore

        doc = Document(file_path)
        return "\n".join(p.text for p in doc.paragraphs)
    except Exception:
        pass

    text_runs: List[str] = []
    with zipfile.ZipFile(file_path) as zf:
        xml_content = zf.read("word/document.xml")
    root = ET.fromstring(xml_content)
    namespace = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
    for node in root.findall(".//w:t", namespace):
        if node.text:
            text_runs.append(node.text)
    return "\n".join(text_runs)


def extract_text(file_path: str, extension: str) -> str:
    if extension == ".pdf":
        return _extract_text_from_pdf(file_path)
    if extension == ".docx":
        return _extract_text_from_docx(file_path)
    raise ValueError("Unsupported resume file extension.")


# ---------------- SKILL EXTRACTION ----------------
def extract_skills(text: str) -> List[str]:
    lowered = text.lower()
    found = [skill for skill in SKILLS_DB if skill in lowered]
    return sorted(set(found))


def parse_resume(file_path: str, extension: str) -> Tuple[str, List[str]]:
    text = extract_text(file_path, extension)
    cleaned = re.sub(r"\s+", " ", text).strip()
    skills = extract_skills(cleaned)
    return cleaned, skills
