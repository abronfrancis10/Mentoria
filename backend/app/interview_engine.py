import uuid

interviews = {}

def create_interview(questions):
    interview_id = str(uuid.uuid4())
    interviews[interview_id] = {
        "questions": questions,
        "current_index": 0,
        "answers": []
    }
    return interview_id

def get_next_question(interview_id):
    interview = interviews.get(interview_id)
    if not interview:
        return {"error": "Invalid interview"}

    idx = interview["current_index"]
    total = len(interview["questions"])

    if idx >= total:
        return {"message": "Interview completed"}

    q = interview["questions"][idx]
    interview["current_index"] += 1

    return {
        "question": q["question"],
        "index": idx + 1,
        "total": total
    }

def store_answer(interview_id, answer_text):
    interview = interviews[interview_id]
    idx = interview["current_index"] - 1

    q = interview["questions"][idx]
    interview["answers"].append({
        "question": q["question"],
        "optimal_answer": q["optimal_answer"],
        "candidate_answer": answer_text
    })
