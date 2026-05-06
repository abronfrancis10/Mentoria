import logging
import asyncio
import json
from typing import Optional, Any
from app.services.async_llm_client import async_llm_client

logger = logging.getLogger(__name__)

DEFAULT_QUESTION = "Tell me about a technical project where you solved a meaningful problem. What was your approach and result?"


async def generate_question_async(prompt: str) -> str:
    """
    Main entry point for generating a single question.
    Implements stable fallback: Ollama -> Gemini -> Default.
    """
    if not prompt or not prompt.strip():
        logger.warning("generate_question_async received empty prompt. Using default.")
        return DEFAULT_QUESTION

    # 1. Attempt Ollama
    logger.info(f"Attempting question generation with Ollama model: {async_llm_client.ollama_model_question}...")
    ollama_result = await async_llm_client.generate_ollama(prompt, model=async_llm_client.ollama_model_question)
    if ollama_result:
        return ollama_result

    # 2. Attempt Gemini Fallback
    logger.info("Ollama failed. Attempting question generation with Gemini fallback...")
    gemini_result = await async_llm_client.generate_gemini(prompt)
    if gemini_result:
        return gemini_result

    # 3. Final Default Fallback
    logger.warning("All LLM attempts failed. Returning default question.")
    return DEFAULT_QUESTION


async def generate_json_async(prompt: str) -> Optional[Any]:
    """
    Main entry point for generating JSON with fallback.
    """
    return await async_llm_client.generate_json(prompt)


async def evaluate_response_async(prompt: str) -> str:
    """
    Async evaluation call.
    Uses the robust generate_json logic and returns stringified JSON.
    """
    result = await async_llm_client.generate_json(prompt)
    if result:
        return json.dumps(result)
    return "{}"


def evaluate_response_with_fallback(prompt: str) -> str:
    """Sync wrapper for legacy evaluation calls."""
    try:
        # Use generate_json directly for better parsing than raw string handling
        result = asyncio.run(async_llm_client.generate_json(prompt))
        if result:
            return json.dumps(result)
        return "{}"
    except Exception as e:
        logger.error(f"Sync evaluation failed: {e}")
        return "{}"


def generate_question_with_fallback(prompt: str) -> str:
    """Sync wrapper for legacy question calls."""
    try:
        return asyncio.run(generate_question_async(prompt))
    except Exception as e:
        logger.error(f"Sync question generation failed: {e}")
        return DEFAULT_QUESTION
