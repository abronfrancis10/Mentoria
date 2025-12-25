ROLE_SKILLS = {
    "Backend Developer": [
        "python", "java", "sql", "fastapi", "django", "node"
    ],
    "Frontend Developer": [
        "javascript", "react", "html", "css"
    ],
    "Full Stack Developer": [
        "python", "javascript", "react", "node", "sql"
    ],
    "Data Analyst": [
        "python", "sql", "data analysis", "machine learning"
    ]
}


def detect_role(skills: list):
    scores = {}

    for role, role_skills in ROLE_SKILLS.items():
        match_count = len(set(skills) & set(role_skills))
        scores[role] = match_count

    detected_role = max(scores, key=scores.get)

    return {
        "detected_role": detected_role,
        "match_score": scores[detected_role],
        "all_scores": scores
    }
