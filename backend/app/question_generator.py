QUESTION_BANK = {
    "python": {
        "easy": [
            "What are Python data types?",
            "What is the difference between list and tuple?"
        ],
        "medium": [
            "Explain list comprehensions with an example.",
            "What are decorators in Python?"
        ],
        "hard": [
            "Explain Python memory management.",
            "How does the GIL affect multithreading?"
        ]
    },
    "sql": {
        "easy": [
            "What is SQL?",
            "What is a primary key?"
        ],
        "medium": [
            "Explain JOIN types in SQL.",
            "Difference between WHERE and HAVING?"
        ],
        "hard": [
            "Explain indexing and query optimization.",
            "How do transactions work in SQL?"
        ]
    },
    "fastapi": {
        "easy": [
            "What is FastAPI?",
            "What is an API?"
        ],
        "medium": [
            "How does FastAPI handle async requests?",
            "What are Pydantic models?"
        ],
        "hard": [
            "Explain dependency injection in FastAPI.",
            "How does FastAPI differ from Flask?"
        ]
    }
}


def generate_questions(core_skills: list, secondary_skills: list):
    questions = []

    for skill in core_skills:
        if skill in QUESTION_BANK:
            questions.extend(QUESTION_BANK[skill]["hard"])

    for skill in secondary_skills:
        if skill in QUESTION_BANK:
            questions.extend(QUESTION_BANK[skill]["medium"])

    return questions
