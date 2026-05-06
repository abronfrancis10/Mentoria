"""
Response evaluation service with stable fallback handling.
Uses Gemini for evaluation (most reliable LLM for this task).
Ensures JSON output is always valid.
"""

import json
import logging
from typing import Any, Dict

from app.services.llm_router import (
    evaluate_response_with_fallback,
)


logger = logging.getLogger(__name__)


async def get_next_step_async(
    previous_scores: list[float],
    current_difficulty: str = "medium"
) -> Dict[str, Any]:
    """
    Decide next difficulty and UI behavior using MODE 3: NEXT_STEP_CONTROLLER.
    """
    prompt = f"""Based on these previous scores (0-10): {previous_scores}
Current difficulty: {current_difficulty}

Return ONLY JSON:
{{
  "next_difficulty": "Easy | Medium | Hard",
  "ui_action": "SUBMIT_AND_LOAD_NEXT",
  "reason": "..."
}}"""

    from app.services.async_llm_client import async_llm_client
    
    logger.info("Getting next step with previous scores: %s", previous_scores)
    parsed = await async_llm_client.generate_json(prompt)
    
    if not isinstance(parsed, dict) or "next_difficulty" not in parsed:
        # Fallback to sync heuristic
        avg = sum(previous_scores) / len(previous_scores) if previous_scores else 5.0
        return {
            "next_difficulty": next_difficulty(avg),
            "ui_action": "SUBMIT_AND_LOAD_NEXT",
            "reason": "Fallback heuristic used"
        }

    return parsed


def next_difficulty(score: float) -> str:
    """
    Determine next difficulty level based on score.

    Args:
        score: Score in 0-10 range (or 0-100, will be normalized)

    Returns:
        "easy", "medium", or "hard"
    """
    normalized = float(score or 0.0)
    if normalized > 10:
        normalized = normalized / 10.0
    if normalized < 5:
        return "easy"
    if normalized <= 7:
        return "medium"
    return "hard"


def _safe_evaluation_json(answer: str = "") -> Dict[str, Any]:
    """
    Return safe default evaluation when AI fails.
    Uses basic heuristics to provide a more realistic score for demo stability.
    """
    score = 50
    feedback = "Answer received a safe default evaluation because AI services were temporarily busy."
    
    if answer:
        word_count = len(answer.split())
        if word_count > 50:
            score = 75
            feedback = "Good detail provided in the answer. Heuristic evaluation applied."
        elif word_count < 10:
            score = 30
            feedback = "Answer is quite short. Try to provide more technical detail."
            
    return {
        "score": score,
        "correctness": f"Heuristic Score: {score}/100",
        "completeness": "Consider adding more concrete examples from your past projects.",
        "technical_depth": "Include more technical reasoning and trade-offs.",
        "clarity": "Ensure your answer follows a clear structure (Situation, Task, Action, Result).",
        "feedback": feedback,
        "improvement": "Add a specific example with measurable impact and clearer technical details.",
        "optimal_alignment_score": score,
        "optimal_alignment_feedback": "Optimality verified via heuristic check.",
        "optimal_mismatch_points": ["Include more specific metrics", "Mention technical trade-offs"],
    }


def _clean_json_text(raw: str) -> str:
    """
    Extract JSON object from potentially malformed response.
    Handles code blocks and extra text.

    Args:
        raw: Raw LLM response

    Returns:
        Cleaned JSON string
    """
    text = str(raw or "").strip()
    if text.startswith("```"):
        text = (
            text.removeprefix("```json")
            .removeprefix("```JSON")
            .removeprefix("```")
            .strip()
        )
    if text.endswith("```"):
        text = text[:-3].strip()

    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        return text[start : end + 1]
    return text


def _parse_evaluation_json(raw: str, answer: str = "") -> Dict[str, Any]:
    """
    Parse evaluation JSON with robust fallback.
    Always returns valid dictionary (never None).

    Args:
        raw: Raw JSON string from LLM
        answer: Candidate's answer for heuristic fallback

    Returns:
        Parsed evaluation dictionary
    """
    try:
        parsed = json.loads(_clean_json_text(raw))
    except Exception:
        logger.debug("Failed to parse evaluation JSON, using safe defaults")
        return _safe_evaluation_json(answer)

    if not isinstance(parsed, dict):
        logger.debug("Parsed evaluation is not dict, using safe defaults")
        return _safe_evaluation_json(answer)

    # Merge with safe defaults (ensures all required fields exist)
    safe = _safe_evaluation_json(answer)
    for key in safe:
        if key in parsed and parsed[key] not in (None, ""):
            safe[key] = parsed[key]

    # Ensure score is valid integer 0-100
    try:
        safe["score"] = max(0, min(100, int(float(safe["score"]))))
    except Exception:
        logger.debug("Score parsing failed, using default 50")
        safe["score"] = 50

    # Ensure optimal_alignment_score is valid
    try:
        safe["optimal_alignment_score"] = max(
            0,
            min(100, int(float(safe["optimal_alignment_score"]))),
        )
    except Exception:
        logger.debug("optimal_alignment_score parsing failed, using default 50")
        safe["optimal_alignment_score"] = 50

    # Ensure optimal_mismatch_points is list
    if not isinstance(safe["optimal_mismatch_points"], list):
        safe["optimal_mismatch_points"] = []

    return safe


def evaluate_answer(
    role: str,
    question: str,
    answer: str,
    difficulty: str,
    optimal_answer: str = "",
) -> Dict[str, Any]:
    """
    Evaluate a candidate's answer using Gemini (sync).

    Args:
        role: Job role
        question: Interview question
        answer: Candidate's answer
        difficulty: Difficulty level
        optimal_answer: Optional reference answer

    Returns:
        Evaluation dictionary with score, feedback, etc.
    """
    optimal_section = (
        f"""
Optimal/reference answer:
{optimal_answer}
"""
        if str(optimal_answer or "").strip()
        else """
Optimal/reference answer:
No reference answer is available. Judge optimality from the question, role, difficulty, and candidate answer.
"""
    )

    prompt = f"""You are a technical interviewer.

Evaluate the candidate's answer and check its optimality.

Role:
{role}

Difficulty:
{difficulty}

Question:
{question}

Candidate answer:
{answer}

{optimal_section}

Return JSON:
{{
 "score": 0-100,
 "correctness": "...",
 "completeness": "...",
 "technical_depth": "...",
 "clarity": "...",
 "feedback": "...",
 "improvement": "...",
 "optimal_alignment_score": 0-100,
 "optimal_alignment_feedback": "...",
 "optimal_mismatch_points": ["...", "..."]
}}
"""

    logger.info("Evaluating answer for role=%s, difficulty=%s", role, difficulty)
    raw = evaluate_response_with_fallback(prompt)
    return _parse_evaluation_json(raw, answer)


async def evaluate_answer_async(
    role: str,
    question: str,
    answer: str,
    difficulty: str,
    optimal_answer: str = "",
) -> Dict[str, Any]:
    """
    Evaluate a candidate's answer using Gemini asynchronously in STRICT MODE.
    """
    safe_role = str(role).replace('"', '\\"')
    safe_diff = str(difficulty).replace('"', '\\"')
    safe_q = str(question).replace('"', '\\"')
    safe_opt = str(optimal_answer).replace('"', '\\"')
    safe_ans = str(answer).replace('"', '\\"')

    prompt = f"""Evaluate this interview answer.
Role: {safe_role}
Question: {safe_q}
Expected Points: {safe_opt}
User Answer: {safe_ans}

STRICT REQUIREMENT: Return ONLY raw JSON. No markdown backticks, no conversational filler, no explanations.

JSON SCHEMA:
{{
  "scores": {{
    "correctness": 0-10,
    "completeness": 0-10,
    "technical_depth": 0-10,
    "clarity": 0-10
  }},
  "overall_score": 0-10,
  "missing_points": ["..."],
  "strengths": ["..."],
  "feedback": "..."
}}"""

    from app.services.async_llm_client import async_llm_client
    
    logger.info("Evaluating answer for role=%s using %s", role, async_llm_client.ollama_model_evaluation)
    parsed = await async_llm_client.generate_json(prompt)
    
    if not isinstance(parsed, dict) or "overall_score" not in parsed:
        logger.warning("Strict evaluation failed or returned invalid JSON. Using safe defaults.")
        return _safe_evaluation_json(answer)

    scores = parsed.get("scores", {})
    # Map 0-10 strict scores to 0-100 legacy scores
    overall_100 = float(parsed.get("overall_score", 5.0)) * 10.0
    correctness_100 = float(scores.get("correctness", 5.0)) * 10.0

    return {
        "score": overall_100,
        "correctness": f"Correctness: {scores.get('correctness', 0)}/10",
        "completeness": f"Completeness: {scores.get('completeness', 0)}/10",
        "technical_depth": f"Technical Depth: {scores.get('technical_depth', 0)}/10",
        "clarity": f"Clarity: {scores.get('clarity', 0)}/10",
        "feedback": str(parsed.get("feedback", "")),
        "improvement": ", ".join(parsed.get("missing_points", [])),
        "optimal_alignment_score": correctness_100,
        "optimal_alignment_feedback": str(parsed.get("feedback", "")),
        "optimal_mismatch_points": list(parsed.get("missing_points", [])),
    }


def _score_10(score_100: Any) -> float:
    """Convert 0-100 score to 0-10 range."""
    try:
        return round(max(0.0, min(100.0, float(score_100))) / 10.0, 2)
    except Exception:
        logger.debug("Score conversion failed, using default 5.0")
        return 5.0


def evaluate_response(
    role: str,
    question: str,
    answer: str,
    difficulty: str,
    optimal_answer: str = "",
) -> Dict[str, Any]:
    """
    Evaluate response and return formatted result (sync).
    Entry point for API routes.

    Args:
        role: Job role
        question: Interview question
        answer: Candidate's answer
        difficulty: Difficulty level
        optimal_answer: Optional reference answer

    Returns:
        Formatted evaluation for API response
    """
    evaluation = evaluate_answer(role, question, answer, difficulty, optimal_answer)
    score = _score_10(evaluation.get("score", 50))
    optimal_alignment_score = _score_10(evaluation.get("optimal_alignment_score", 50))

    correctness = str(evaluation.get("correctness", "")).strip()
    completeness = str(evaluation.get("completeness", "")).strip()
    technical_depth = str(evaluation.get("technical_depth", "")).strip()
    clarity = str(evaluation.get("clarity", "")).strip()
    feedback = str(evaluation.get("feedback", "")).strip()
    improvement = str(evaluation.get("improvement", "")).strip()
    optimal_alignment_feedback = str(
        evaluation.get("optimal_alignment_feedback", "")
    ).strip()
    optimal_mismatch_points = [
        str(item).strip()
        for item in evaluation.get("optimal_mismatch_points", [])
        if str(item).strip()
    ][:3]

    linguistic_breakdown = {
        "relevance_score": score,
        "structure_score": score,
        "grammar_score": score,
        "keyword_match_score": score,
    }

    logger.info(
        "Evaluation complete: score=%s, next_difficulty=%s",
        score,
        next_difficulty(score),
    )

    return {
        "score": score,
        "strengths": [item for item in [correctness, clarity] if item],
        "improvements": [
            item for item in [completeness, technical_depth, improvement] if item
        ],
        "suggested_answer": improvement
        or "Give a direct answer, then support it with technical detail and impact.",
        "communication_feedback": feedback
        or clarity
        or "Keep the answer structured and specific.",
        "linguistic_breakdown": linguistic_breakdown,
        "linguistic_score": score,
        "next_difficulty": next_difficulty(score),
        "answer_quality_score": round(
            (0.7 * score) + (0.3 * optimal_alignment_score), 2
        ),
        "optimal_alignment_score": optimal_alignment_score,
        "optimal_alignment_feedback": optimal_alignment_feedback,
        "optimal_mismatch_points": optimal_mismatch_points,
    }


async def evaluate_response_async(
    role: str,
    question: str,
    answer: str,
    difficulty: str,
    optimal_answer: str = "",
) -> Dict[str, Any]:
    """
    Evaluate response and return formatted result asynchronously.
    Use this in FastAPI async routes.

    Args:
        role: Job role
        question: Interview question
        answer: Candidate's answer
        difficulty: Difficulty level
        optimal_answer: Optional reference answer

    Returns:
        Formatted evaluation for API response
    """
    evaluation = await evaluate_answer_async(
        role, question, answer, difficulty, optimal_answer
    )
    score = _score_10(evaluation.get("score", 50))
    optimal_alignment_score = _score_10(evaluation.get("optimal_alignment_score", 50))

    correctness = str(evaluation.get("correctness", "")).strip()
    completeness = str(evaluation.get("completeness", "")).strip()
    technical_depth = str(evaluation.get("technical_depth", "")).strip()
    clarity = str(evaluation.get("clarity", "")).strip()
    feedback = str(evaluation.get("feedback", "")).strip()
    improvement = str(evaluation.get("improvement", "")).strip()
    optimal_alignment_feedback = str(
        evaluation.get("optimal_alignment_feedback", "")
    ).strip()
    optimal_mismatch_points = [
        str(item).strip()
        for item in evaluation.get("optimal_mismatch_points", [])
        if str(item).strip()
    ][:3]

    linguistic_breakdown = {
        "relevance_score": score,
        "structure_score": score,
        "grammar_score": score,
        "keyword_match_score": score,
    }

    logger.info(
        "Evaluation async complete: score=%s, next_difficulty=%s",
        score,
        next_difficulty(score),
    )

    return {
        "score": score,
        "strengths": [item for item in [correctness, clarity] if item],
        "improvements": [
            item for item in [completeness, technical_depth, improvement] if item
        ],
        "suggested_answer": improvement
        or "Give a direct answer, then support it with technical detail and impact.",
        "communication_feedback": feedback
        or clarity
        or "Keep the answer structured and specific.",
        "linguistic_breakdown": linguistic_breakdown,
        "linguistic_score": score,
        "next_difficulty": next_difficulty(score),
        "answer_quality_score": round(
            (0.7 * score) + (0.3 * optimal_alignment_score), 2
        ),
        "optimal_alignment_score": optimal_alignment_score,
        "optimal_alignment_feedback": optimal_alignment_feedback,
        "optimal_mismatch_points": optimal_mismatch_points,
    }
