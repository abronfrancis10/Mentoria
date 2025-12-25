KEYWORDS = {
    "python memory management": [
        "heap", "stack", "garbage collection", "reference counting"
    ],
    "gil": [
        "global interpreter lock", "thread", "concurrency"
    ],
    "fastapi dependency injection": [
        "depends", "dependency", "reusable", "injection"
    ],
    "sql indexing": [
        "index", "query optimization", "performance"
    ]
}


def evaluate_answer(question: str, answer: str):
    question_key = None
    question_lower = question.lower()

    for key in KEYWORDS:
        if key in question_lower:
            question_key = key
            break

    matched_keywords = []
    answer_lower = answer.lower()

    if question_key:
        for keyword in KEYWORDS[question_key]:
            if keyword in answer_lower:
                matched_keywords.append(keyword)

    # scoring
    keyword_score = len(matched_keywords)
    length_score = 1 if len(answer.split()) > 30 else 0
    total_score = keyword_score + length_score

    feedback = []

    if keyword_score == 0:
        feedback.append("Answer lacks key technical concepts.")
    if length_score == 0:
        feedback.append("Answer is too short; provide more explanation.")
    if total_score >= 3:
        feedback.append("Good structured answer with relevant details.")

    return {
        "score": min(total_score * 2.5, 10),
        "matched_keywords": matched_keywords,
        "feedback": feedback
    }
