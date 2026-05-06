import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


DIFFICULTIES = ("easy", "medium", "hard")
DEFAULT_TOTAL_QUESTIONS = 10
interviews: Dict[str, Dict[str, Any]] = {}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _normalize_question_item(
    item: Dict[str, Any], default_difficulty: str = "medium"
) -> Dict[str, str]:
    question = str(item.get("question", "")).strip()
    optimal_answer = str(item.get("optimal_answer", "")).strip()
    difficulty = str(item.get("difficulty", default_difficulty)).strip().lower()
    if difficulty not in DIFFICULTIES:
        difficulty = default_difficulty
    return {
        "question": question,
        "optimal_answer": optimal_answer
        or f"Provide a clear, structured answer for: {question}",
        "difficulty": difficulty,
    }


def _normalize_question_bank(raw_questions: object) -> Dict[str, List[Dict[str, str]]]:
    bank: Dict[str, List[Dict[str, str]]] = {d: [] for d in DIFFICULTIES}

    if isinstance(raw_questions, dict):
        has_difficulty_keys = any(k in raw_questions for k in DIFFICULTIES)
        if has_difficulty_keys:
            for difficulty in DIFFICULTIES:
                items = raw_questions.get(difficulty, []) or []
                for item in items:
                    if isinstance(item, dict):
                        normalized = _normalize_question_item(item, difficulty)
                        if normalized["question"]:
                            bank[difficulty].append(normalized)
                    elif isinstance(item, str):
                        bank[difficulty].append(
                            _normalize_question_item(
                                {
                                    "question": item,
                                    "optimal_answer": "",
                                    "difficulty": difficulty,
                                },
                                difficulty,
                            )
                        )
            return bank

    if isinstance(raw_questions, list):
        for item in raw_questions:
            if isinstance(item, dict):
                normalized = _normalize_question_item(item, "medium")
                if normalized["question"]:
                    bank["medium"].append(normalized)
            elif isinstance(item, str):
                bank["medium"].append(
                    _normalize_question_item(
                        {"question": item, "optimal_answer": "", "difficulty": "medium"}
                    )
                )

    return bank


def _difficulty_priority(difficulty: str) -> List[str]:
    if difficulty == "easy":
        return ["easy", "medium", "hard"]
    if difficulty == "hard":
        return ["hard", "medium", "easy"]
    return ["medium", "easy", "hard"]


def _pick_next_question(interview: Dict[str, Any]) -> Optional[Dict[str, str]]:
    preferred = interview.get("current_difficulty", "medium")
    for difficulty in _difficulty_priority(preferred):
        bucket = interview["question_bank"].get(difficulty, [])
        while bucket:
            candidate = bucket.pop(0)
            question_key = candidate["question"].strip().lower()
            if not question_key or question_key in interview["asked_question_keys"]:
                continue
            interview["asked_question_keys"].add(question_key)
            candidate["difficulty"] = difficulty
            return candidate
    return None


def _init_transition_counts() -> Dict[str, int]:
    return {
        "easy_to_medium": 0,
        "easy_to_hard": 0,
        "medium_to_easy": 0,
        "medium_to_hard": 0,
        "hard_to_medium": 0,
        "hard_to_easy": 0,
    }


def create_interview(
    questions: object,
    role: str = "",
    skills: Optional[List[str]] = None,
    user_id: str = "anonymous",
    total_questions: int = DEFAULT_TOTAL_QUESTIONS,
    initial_difficulty: str = "medium",
) -> str:
    interview_id = str(uuid.uuid4())
    bank = _normalize_question_bank(questions)

    # We respect the total_questions requested by the user.
    # Dynamic generation will fill the bank as needed.
    target_total = max(1, total_questions)

    if initial_difficulty not in DIFFICULTIES:
        initial_difficulty = "medium"

    interviews[interview_id] = {
        "interview_id": interview_id,
        "role": role,
        "skills": list(skills or []),
        "user_id": str(user_id or "anonymous").strip() or "anonymous",
        "started_at": _now_iso(),
        "question_bank": bank,
        "current_question": None,
        "current_difficulty": initial_difficulty,
        "answers": [],
        "answer_events": [],
        "asked_question_keys": set(),
        "answered_count": 0,
        "total_questions": target_total,
        "difficulty_history": [initial_difficulty],
        "question_level_history": [],
        "difficulty_transition_counts": _init_transition_counts(),
        "final_difficulty_reached": initial_difficulty,
    }
    return interview_id


def inject_question(interview_id: str, question: Dict[str, str]) -> None:
    interview = interviews.get(interview_id)
    if not interview:
        return
    diff = question.get("difficulty", "medium")
    if diff not in interview["question_bank"]:
        interview["question_bank"][diff] = []
    interview["question_bank"][diff].append(question)


def get_next_question(interview_id: str) -> Dict[str, Any]:
    interview = interviews.get(interview_id)
    if not interview:
        return {"error": "Invalid interview id"}

    if interview["answered_count"] >= interview["total_questions"]:
        return {"message": "Interview completed"}

    if interview["current_question"] is None:
        question = _pick_next_question(interview)
        if question is None:
            return {"message": "Interview completed"}
        interview["current_question"] = question

    question_number = interview["answered_count"] + 1
    current = interview["current_question"]
    return {
        "question": current["question"],
        "question_number": question_number,
        "total_questions": interview["total_questions"],
        "difficulty": current.get(
            "difficulty", interview.get("current_difficulty", "medium")
        ),
    }


def get_current_question(interview_id: str) -> Optional[Dict[str, str]]:
    interview = interviews.get(interview_id)
    if not interview:
        return None
    return interview.get("current_question")


def get_current_difficulty(interview_id: str) -> str:
    interview = interviews.get(interview_id)
    if not interview:
        return "medium"
    return str(interview.get("current_difficulty", "medium"))


def set_current_difficulty(interview_id: str, difficulty: str) -> str:
    interview = interviews.get(interview_id)
    if not interview:
        return "medium"

    next_difficulty = str(difficulty or "").strip().lower()
    if next_difficulty not in DIFFICULTIES:
        next_difficulty = "medium"

    current = str(interview.get("current_difficulty", "medium"))
    if current != next_difficulty:
        key = f"{current}_to_{next_difficulty}"
        if key in interview["difficulty_transition_counts"]:
            interview["difficulty_transition_counts"][key] += 1
        interview["difficulty_history"].append(next_difficulty)

    interview["current_difficulty"] = next_difficulty
    interview["final_difficulty_reached"] = next_difficulty
    return next_difficulty


def submit_answer(interview_id: str, answer_text: str) -> str:
    interview = interviews.get(interview_id)
    if not interview:
        return ""

    current = interview.get("current_question")
    if not current:
        return ""

    question_number = interview["answered_count"] + 1
    question_difficulty = current.get(
        "difficulty", interview.get("current_difficulty", "medium")
    )
    interview["answers"].append(
        {
            "question_number": question_number,
            "question": current["question"],
            "optimal_answer": current["optimal_answer"],
            "candidate_answer": answer_text,
            "difficulty": question_difficulty,
            "timestamp": _now_iso(),
        }
    )
    interview["question_level_history"].append(
        {
            "question_number": question_number,
            "difficulty": question_difficulty,
            "score": None,
        }
    )
    interview["answered_count"] += 1
    interview["current_question"] = None
    return current["optimal_answer"]


def add_answer_event(interview_id: str, event: Dict[str, Any]) -> None:
    interview = interviews.get(interview_id)
    if not interview:
        return
    interview["answer_events"].append(dict(event))
    question_number = int(event.get("question_number", 0) or 0)
    score = event.get("overall_score")
    if question_number > 0 and score is not None:
        for item in interview["question_level_history"]:
            if (
                int(item.get("question_number", 0)) == question_number
                and item.get("score") is None
            ):
                item["score"] = round(float(score), 2)
                break


def get_interview_state(interview_id: str) -> Optional[Dict[str, Any]]:
    interview = interviews.get(interview_id)
    if not interview:
        return None

    return {
        "interview_id": interview["interview_id"],
        "user_id": interview["user_id"],
        "role": interview["role"],
        "skills": list(interview["skills"]),
        "started_at": interview["started_at"],
        "answered_count": int(interview["answered_count"]),
        "total_questions": int(interview["total_questions"]),
        "current_difficulty": str(interview["current_difficulty"]),
        "difficulty_history": list(interview["difficulty_history"]),
        "question_level_history": [
            dict(x) for x in interview["question_level_history"]
        ],
        "difficulty_transition_counts": dict(interview["difficulty_transition_counts"]),
        "final_difficulty_reached": str(interview["final_difficulty_reached"]),
        "answers": [dict(x) for x in interview["answers"]],
        "answer_events": [dict(x) for x in interview["answer_events"]],
    }
