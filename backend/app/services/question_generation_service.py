import logging
import asyncio
import json
from typing import Dict, List

logger = logging.getLogger(__name__)


def _skills_text(skills: List[str]) -> str:
    """Format skills list for LLM prompt."""
    cleaned = [str(skill).strip() for skill in skills or [] if str(skill).strip()]
    return ", ".join(cleaned) if cleaned else "general software engineering"


def _clean_question(text: str) -> str:
    """Clean and normalize question text."""
    question = " ".join(str(text or "").split()).strip()
    question = question.strip('"').strip("'").strip()

    # Remove common prefixes
    prefixes = ["Question:", "Interview Question:"]
    for prefix in prefixes:
        if question.lower().startswith(prefix.lower()):
            question = question[len(prefix) :].strip()

    return question


async def generate_single_question_async(
    role: str, skills: List[str], difficulty: str, category: str = "technical"
) -> str:
    """
    Generate a single interview question asynchronously in STRICT MODE.
    """
    safe_role = str(role).replace('"', '\\"')
    safe_diff = str(difficulty).replace('"', '\\"')
    safe_cat = str(category).replace('"', '\\"')
    
    prompt = f"""Generate ONE {safe_cat} interview question for a {safe_role} focusing on {json.dumps(skills)}.
Difficulty: {safe_diff}.

STRICT REQUIREMENT: Return ONLY raw JSON. No markdown backticks, no conversational filler, no explanations.

JSON SCHEMA:
{{
  "question": "...",
  "expected_answer": ["point 1", "point 2"],
  "difficulty": "{safe_diff}"
}}"""

    from app.services.async_llm_client import async_llm_client
    
    logger.info(f"Requesting {category} question for role={role} using {async_llm_client.ollama_model_question}")
    result = await async_llm_client.generate_json(prompt)
    
    if isinstance(result, dict) and result.get("question"):
        return _clean_question(result["question"])

    # Final fallback - use static high quality questions
    try:
        from app.services.static_questions import get_static_questions
        static = get_static_questions(role, 1)
        if static:
            return _clean_question(static[0]["question"])
    except Exception:
        pass

    fallbacks = {
        "technical": "Tell me about a technical challenge you faced and how you solved it.",
        "behavioral": "Describe a time when you had to work with a difficult teammate.",
        "scenario": "How would you approach designing a scalable system for a sudden traffic spike?"
    }
    return fallbacks.get(category, fallbacks["technical"])


def generate_single_question(role: str, skills: List[str], difficulty: str) -> str:
    """Synchronous wrapper for generate_single_question_async."""
    try:
        return asyncio.run(generate_single_question_async(role, skills, difficulty))
    except Exception as e:
        logger.error(f"Sync question generation failed: {e}")
        return "Tell me about a technical challenge you faced and how you solved it."


def generate_question(role: str, difficulty: str, resume_text: str) -> str:
    """Legacy sync entry point."""
    return generate_single_question(role, [], difficulty)


def generate_questions(
    role: str, skills: List[str], difficulty: str
) -> Dict[str, List[str]]:
    """Legacy sync entry point for multiple categories."""
    q = generate_single_question(role, skills, difficulty)
    return {"technical": [q], "behavioral": [], "scenario": []}


def generate_questions_with_answers(
    role: str,
    skills: List[str],
    difficulty: str,
    count: int = 10,
) -> List[Dict[str, str]]:
    """Legacy sync entry point for multiple questions with answers."""
    try:
        return asyncio.run(
            generate_questions_with_answers_async(role, skills, difficulty, count)
        )
    except Exception as e:
        logger.error(f"Sync questions with answers generation failed: {e}")
        return [
            {
                "question": "Tell me about a technical challenge you faced.",
                "optimal_answer": "",
                "difficulty": difficulty,
            }
        ]


async def generate_questions_async(
    role: str, skills: List[str], difficulty: str
) -> Dict[str, List[str]]:
    """
    Generate a bundle of questions (technical, behavioral, scenario) asynchronously.
    """
    safe_role = str(role).replace('"', '\\"')
    safe_diff = str(difficulty).replace('"', '\\"')
    
    prompt = f"""You are an AI Interview Engine operating in STRICT MODE.
You must follow instructions EXACTLY and return ONLY valid JSON.
Do NOT include explanations, markdown, or extra text.

----------------------------------------
MODE 1: GENERATE_BUNDLE
----------------------------------------
Goal: Generate a bundle of THREE high-quality interview questions (1 technical, 1 behavioral, 1 scenario).

INPUT:
{{
  "mode": "GENERATE_BUNDLE",
  "role": "{safe_role}",
  "skills": {json.dumps(skills)},
  "difficulty": "{safe_diff}"
}}

OUTPUT FORMAT (JSON):
{{
  "technical": ["..."],
  "behavioral": ["..."],
  "scenario": ["..."]
}}"""

    from app.services.async_llm_client import async_llm_client
    
    logger.info(f"Generating question bundle for role={role}, difficulty={difficulty}")
    result = await async_llm_client.generate_json(prompt)
    
    if isinstance(result, dict) and all(k in result for k in ["technical", "behavioral", "scenario"]):
        return {
            "technical": [_clean_question(q) for q in result.get("technical", []) if q],
            "behavioral": [_clean_question(q) for q in result.get("behavioral", []) if q],
            "scenario": [_clean_question(q) for q in result.get("scenario", []) if q]
        }

    # Parallel fallback if bundle generation fails
    logger.warning("Bundle generation failed, falling back to individual calls or static data.")
    
    try:
        from app.services.static_questions import get_static_questions
        static_bundle = get_static_questions(role, 3)
        if static_bundle and len(static_bundle) >= 3:
            return {
                "technical": [_clean_question(static_bundle[0]["question"])],
                "behavioral": [_clean_question(static_bundle[1]["question"])],
                "scenario": [_clean_question(static_bundle[2]["question"])]
            }
    except Exception:
        pass

    tasks = [
        generate_single_question_async(role, skills, difficulty, "technical"),
        generate_single_question_async(role, skills, difficulty, "behavioral"),
        generate_single_question_async(role, skills, difficulty, "scenario")
    ]
    results = await asyncio.gather(*tasks)
    
    return {
        "technical": [results[0]],
        "behavioral": [results[1]],
        "scenario": [results[2]]
    }


async def generate_questions_with_answers_async(
    role: str,
    skills: List[str],
    difficulty: str,
    count: int = 10,
) -> List[Dict[str, str]]:
    """
    Generate multiple questions with their optimal answers asynchronously.
    """
    safe_count = max(1, min(int(count or 1), 20))

    # Optimization: For a single question, use the specialized single-question logic
    if safe_count == 1:
        logger.info(f"Generating single sequential question for role={role}")
        question_text = await generate_single_question_async(role, skills, difficulty)
        return [
            {
                "question": question_text,
                "optimal_answer": f"Expected technical points for: {question_text}",
                "difficulty": str(difficulty or "medium").strip().lower()
            }
        ]

    safe_role = str(role).replace('"', '\\"')
    safe_diff = str(difficulty).replace('"', '\\"')

    prompt = f"""Generate {safe_count} interview questions for a {safe_role} focusing on {json.dumps(skills)}.
Difficulty: {safe_diff}.

STRICT REQUIREMENT: Return ONLY raw JSON. No markdown backticks, no conversational filler, no explanations.

JSON SCHEMA (List of objects):
[
  {{
    "question": "...",
    "expected_answer": ["point 1", "point 2"],
    "difficulty": "{safe_diff}"
  }}
]"""

    from app.services.async_llm_client import async_llm_client
    
    logger.info(f"Generating {safe_count} questions for role={role} using {async_llm_client.ollama_model_question}")
    result = await async_llm_client.generate_json(prompt)
    
    if isinstance(result, list) and len(result) > 0:
        processed = []
        for item in result:
            if isinstance(item, dict) and item.get("question"):
                # Join expected answer points into a string for the legacy schema
                expected = item.get("expected_answer")
                opt_ans = ". ".join(expected) if isinstance(expected, list) else str(expected or "")
                
                processed.append({
                    "question": _clean_question(item.get("question")),
                    "optimal_answer": opt_ans.strip(),
                    "difficulty": str(item.get("difficulty") or difficulty).strip().lower()
                })
        if processed:
            return processed

    # Fallback loop using single strict calls or static data
    logger.warning("Batch strict generation failed. Falling back to sequential strict calls or static data.")
    
    try:
        from app.services.static_questions import get_static_questions
        static_bundle = get_static_questions(role, safe_count)
        if static_bundle and len(static_bundle) >= safe_count:
            processed = []
            for item in static_bundle:
                expected = item.get("expected_answer", [])
                opt_ans = ". ".join(expected) if isinstance(expected, list) else str(expected or "")
                processed.append({
                    "question": _clean_question(item.get("question")),
                    "optimal_answer": opt_ans.strip(),
                    "difficulty": str(item.get("difficulty") or difficulty).strip().lower()
                })
            return processed
    except Exception as e:
        logger.error(f"Failed to load static questions: {e}")

    questions: List[Dict[str, str]] = []
    for i in range(safe_count):
        question_text = await generate_single_question_async(role, skills, difficulty)
        questions.append(
            {
                "question": question_text,
                "optimal_answer": f"Expected technical points for: {question_text}",
                "difficulty": str(difficulty or "medium").strip().lower() or "medium",
            }
        )

    return questions
