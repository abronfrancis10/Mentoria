import pdfplumber
import spacy

nlp = spacy.load("en_core_web_sm")

SKILLS_DB = [
    "python", "java", "c++", "sql", "javascript",
    "react", "node", "fastapi", "django",
    "machine learning", "data analysis",
    "html", "css"
]

def extract_text_from_pdf(file_path: str) -> str:
    text = ""
    with pdfplumber.open(file_path) as pdf:
        for page in pdf.pages:
            text += page.extract_text() or ""
    return text.lower()


def extract_skills(text: str):
    found_skills = []
    for skill in SKILLS_DB:
        if skill in text:
            found_skills.append(skill)
    return list(set(found_skills))


def extract_entities(text: str):
    doc = nlp(text)
    education = []
    experience = []

    for ent in doc.ents:
        if ent.label_ == "ORG":
            experience.append(ent.text)
        if ent.label_ == "DATE":
            education.append(ent.text)

    return {
        "education": list(set(education)),
        "experience": list(set(experience))
    }


def parse_resume(file_path: str):
    text = extract_text_from_pdf(file_path)
    skills = extract_skills(text)
    entities = extract_entities(text)

    return {
        "skills": skills,
        "education": entities["education"],
        "experience": entities["experience"]
    }
