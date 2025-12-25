import uuid

INTERVIEWS = {}


def create_interview(questions: list):
    interview_id = str(uuid.uuid4())

    INTERVIEWS[interview_id] = {
        "questions": questions,
        "current_index": 0,
        "evaluations": []
    }

    return interview_id


def get_current_question(interview_id: str):
    interview = INTERVIEWS.get(interview_id)

    if not interview:
        return None

    idx = interview["current_index"]

    if idx >= len(interview["questions"]):
        return None

    return interview["questions"][idx]


def submit_answer(interview_id: str, evaluation: dict):
    interview = INTERVIEWS.get(interview_id)

    if not interview:
        return False

    # Prevent double submission
    if interview["current_index"] < len(interview["questions"]):
        interview["evaluations"].append(evaluation)
        interview["current_index"] += 1

    return True


def is_interview_complete(interview_id: str):
    interview = INTERVIEWS.get(interview_id)

    if not interview:
        return True

    return interview["current_index"] >= len(interview["questions"])


def get_summary(interview_id: str):
    interview = INTERVIEWS.get(interview_id)

    if not interview:
        return {}

    return {
        "total_questions": len(interview["questions"]),
        "evaluations": interview["evaluations"]
    }
