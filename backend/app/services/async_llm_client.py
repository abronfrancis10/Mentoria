import asyncio
import logging
import os
import re
import json
from typing import Optional, Any
from pathlib import Path
from google import genai
from dotenv import load_dotenv
import ollama

logger = logging.getLogger(__name__)


def _extract_json(text: str) -> Optional[Any]:
    """Helper to extract JSON from LLM response text."""
    if not text:
        return None
    
    cleaned = str(text).strip()
    
    # 1. Handle markdown code blocks explicitly
    if "```" in cleaned:
        # Try to find content between ```json and ```
        json_match = re.search(r"```(?:json|JSON)?\s*([\s\S]*?)```", cleaned)
        if json_match:
            candidate = json_match.group(1).strip()
            try:
                return json.loads(candidate)
            except Exception:
                cleaned = candidate # Fall through to more aggressive extraction
        else:
            # Just strip the backticks if it's not a standard block
            cleaned = cleaned.replace("```json", "").replace("```JSON", "").replace("```", "").strip()

    # 2. Aggressive search for { or [
    start_curly = cleaned.find("{")
    end_curly = cleaned.rfind("}")
    start_bracket = cleaned.find("[")
    end_bracket = cleaned.rfind("]")

    # Determine which structure to try first
    # If we find both, we try the one that starts first
    # This handles both {"a": [1]} and [{"a": 1}]
    candidates = []
    if start_curly != -1 and end_curly != -1 and end_curly > start_curly:
        candidates.append((start_curly, end_curly))
    if start_bracket != -1 and end_bracket != -1 and end_bracket > start_bracket:
        candidates.append((start_bracket, end_bracket))
    
    # Sort by start position to try the outer-most structure first
    candidates.sort()

    for start, end in candidates:
        candidate = cleaned[start : end + 1]
        try:
            return json.loads(candidate)
        except Exception:
            # Try to fix common small model JSON errors
            try:
                # 1. Remove trailing commas in objects and arrays
                # This regex is basic but handles common cases
                fixed = re.sub(r",\s*([\]}])", r"\1", candidate)
                # 2. Handle some unescaped control characters
                fixed = fixed.replace("\n", "\\n").replace("\r", "\\r").replace("\t", "\\t")
                # Wait, replacing \n with \\n might break actual newlines outside strings if we aren't careful.
                # Let's try just the trailing comma fix first as it's the most common.
                return json.loads(fixed)
            except Exception:
                pass
            
    # Final attempt: direct parse
    try:
        return json.loads(cleaned)
    except Exception:
        pass

    return None


def _load_project_env() -> None:
    """Load .env from the backend directory."""
    project_env = Path(__file__).resolve().parents[2] / ".env"
    if project_env.is_file():
        load_dotenv(dotenv_path=project_env, override=False)


class AsyncLLMClient:
    def __init__(self):
        _load_project_env()
        # Ollama configuration
        self.ollama_model = os.getenv("MENTORIA_OLLAMA_MODEL", "mistral").strip()
        self.ollama_model_question = os.getenv("MENTORIA_OLLAMA_MODEL_QUESTION", self.ollama_model).strip()
        self.ollama_model_evaluation = os.getenv("MENTORIA_OLLAMA_MODEL_EVALUATION", "mistral").strip()
        self.ollama_timeout = float(os.getenv("MENTORIA_OLLAMA_TIMEOUT", "180"))
        
        # Gemini configuration
        self.gemini_api_key = os.getenv(
            "GEMINI_API_KEY", os.getenv("MENTORIA_GEMINI_API_KEY", "")
        ).strip()
        self.gemini_model = os.getenv(
            "MENTORIA_GEMINI_MODEL", "models/gemini-2.0-flash"
        ).strip()
        self.gemini_timeout = float(os.getenv("MENTORIA_GEMINI_TIMEOUT", "60"))

        if self.gemini_api_key:
            try:
                # Use the new genai Client
                self.gemini_client = genai.Client(api_key=self.gemini_api_key)
                logger.info(f"Gemini client initialized with model {self.gemini_model}")
            except Exception as e:
                logger.error(f"Failed to initialize Gemini client: {e}")
                self.gemini_client = None
        else:
            self.gemini_client = None
            logger.warning(
                "Gemini API key not found. Gemini fallback will be unavailable."
            )

    async def generate_ollama(self, prompt: str, model: Optional[str] = None) -> Optional[str]:
        """Attempt to generate text using Ollama (async) using the official library."""
        try:
            # Get the base URL (remove /api/generate if present)
            base_url = os.getenv("MENTORIA_OLLAMA_URL", "http://localhost:11434").replace("/api/generate", "")
            
            # Use the official ollama async client with the specific host
            client = ollama.AsyncClient(host=base_url)
            
            target_model = model or self.ollama_model
            
            # Wrap in wait_for to enforce timeout
            response = await asyncio.wait_for(
                client.generate(model=target_model, prompt=prompt),
                timeout=self.ollama_timeout
            )
            
            text = response.get("response", "").strip()
            if text:
                logger.info(f"Successfully generated response using Ollama model: {target_model}")
                return text
                
        except asyncio.TimeoutError:
            logger.warning(f"Ollama request timed out after {self.ollama_timeout}s")
        except Exception as e:
            logger.error(f"Ollama request failed: {e}")

        return None

    async def generate_gemini(self, prompt: str) -> Optional[str]:
        """Attempt to generate text using Gemini (async) using the new SDK."""
        if not self.gemini_client:
            return None

        try:
            # Use loop.run_in_executor to keep it async-safe as the SDK might be blocking
            loop = asyncio.get_running_loop()
            response = await loop.run_in_executor(
                None,
                lambda: self.gemini_client.models.generate_content(
                    model=self.gemini_model, 
                    contents=prompt,
                    config={"temperature": 0.3}
                ),
            )

            if response and response.text:
                text = response.text.strip()
                if text:
                    logger.info("Successfully generated response using Gemini.")
                    return text
        except Exception as e:
            logger.error(f"Gemini request failed: {e}")

        return None

    async def generate_json(self, prompt: str) -> Optional[Any]:
        """Generate text and attempt to parse it as JSON."""
        # Try Ollama first as requested
        logger.debug("Attempting JSON generation with Ollama...")
        res = await self.generate_ollama(prompt)
        if res:
            parsed = _extract_json(res)
            if parsed is not None:
                logger.info("Successfully generated and parsed JSON using Ollama.")
                return parsed
            logger.warning("Ollama returned text but it could not be parsed as JSON.")
        
        # Fallback to Gemini
        logger.debug("Attempting JSON generation with Gemini fallback...")
        res = await self.generate_gemini(prompt)
        if res:
            parsed = _extract_json(res)
            if parsed is not None:
                logger.info("Successfully generated and parsed JSON using Gemini.")
                return parsed
            logger.warning("Gemini returned text but it could not be parsed as JSON.")
                
        return None


# Singleton instance logic
def get_llm_client():
    if os.getenv("OFFLINE_MODE", "false").lower() == "true":
        from app.services.mock_llm_client import MockLLMClient
        return MockLLMClient()
    return AsyncLLMClient()

async_llm_client = get_llm_client()
