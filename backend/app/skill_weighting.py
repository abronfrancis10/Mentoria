ROLE_SKILL_WEIGHTS = {
    "Backend Developer": {
        "core": ["python", "sql", "fastapi", "django"],
        "secondary": ["java", "node", "html", "css"]
    },
    "Frontend Developer": {
        "core": ["javascript", "react", "html", "css"],
        "secondary": ["node"]
    },
    "Full Stack Developer": {
        "core": ["python", "javascript", "react", "sql"],
        "secondary": ["node", "html", "css"]
    },
    "Data Analyst": {
        "core": ["python", "sql", "data analysis"],
        "secondary": ["machine learning"]
    }
}


def weight_skills(role: str, skills: list):
    core_skills = []
    secondary_skills = []

    role_data = ROLE_SKILL_WEIGHTS.get(role, {})

    for skill in skills:
        if skill in role_data.get("core", []):
            core_skills.append(skill)
        elif skill in role_data.get("secondary", []):
            secondary_skills.append(skill)

    return {
        "core_skills": core_skills,
        "secondary_skills": secondary_skills
    }
