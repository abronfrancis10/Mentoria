from typing import List


ROLE_KEYWORDS = {
    "frontend": {"react", "javascript", "typescript", "html", "css"},
    "backend": {"python", "java", "sql", "fastapi", "django", "flask"},
    "data": {"machine learning", "data analysis", "nlp", "python", "sql"},
    "devops": {"docker", "kubernetes", "aws", "azure", "gcp"},
}


# ---------------- ROLE REFINEMENT ----------------
def refine_role(role_input: str, skills: List[str]) -> str:
    role_lower = (role_input or "").strip().lower()
    if not role_lower:
        role_lower = "software engineer"

    skill_set = set(s.lower() for s in skills)
    scores = {
        domain: len(skill_set.intersection(words))
        for domain, words in ROLE_KEYWORDS.items()
    }
    best_domain = max(scores, key=scores.get) if scores else "backend"

    if scores.get(best_domain, 0) == 0:
        return role_input.strip() or "Software Engineer"

    role_map = {
        "frontend": "Frontend Developer",
        "backend": "Backend Software Engineer",
        "data": "Data / ML Engineer",
        "devops": "DevOps Engineer",
    }
    return role_map.get(best_domain, role_input.strip() or "Software Engineer")
