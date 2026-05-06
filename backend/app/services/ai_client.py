import json
import logging
import os
import re
from pathlib import Path
from typing import Any, Dict, Optional

import requests

try:
    import google.generativeai as genai  # type: ignore
except Exception:  # pragma: no cover - optional dependency guard
    genai = None  # type: ignore

try:
    from dotenv import load_dotenv
except Exception:  # pragma: no cover - optional dependency guard
    load_dotenv = None  # type: ignore


logger = logging.getLogger(__name__)
_ENV_READY = False


def _load_project_env() -> None:
    global _ENV_READY
    if _ENV_READY:
        return
    if load_dotenv is None:
        _ENV_READY = True
        return

    project_env = Path(__file__).resolve().parents[2] / ".env"
    if project_env.is_file():
        load_dotenv(dotenv_path=project_env, override=False)
    _ENV_READY = True


def _clean_llm_text(text: str) -> str:
    cleaned = str(text or "").strip()
    if not cleaned:
        return ""

    cleaned = re.sub(r"```(?:json)?\s*", "", cleaned, flags=re.IGNORECASE)
    cleaned = cleaned.replace("```", "")
    return cleaned.strip()


def _extract_json_object(text: str) -> Optional[Dict[str, Any]]:
    cleaned = _clean_llm_text(text)
    if not cleaned:
        return None

    candidates = [cleaned]
    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start != -1 and end != -1 and end > start:
        candidates.append(cleaned[start : end + 1])

    for candidate in candidates:
        try:
            parsed = json.loads(candidate)
        except Exception:
            continue
        if isinstance(parsed, dict):
            return parsed
    return None


class AIClient:
    def __init__(self) -> None:
        _load_project_env()
        self.model = (
            os.getenv(
                "MENTORIA_MODEL", os.getenv("MENTORIA_OLLAMA_MODEL", "mistral")
            ).strip()
            or "mistral"
        )
        self.ollama_url = os.getenv(
            "MENTORIA_OLLAMA_URL", "http://localhost:11434/api/generate"
        ).strip()
        self.ollama_timeout = float(os.getenv("MENTORIA_OLLAMA_TIMEOUT", "10"))
        self.gemini_api_key = os.getenv(
            "GEMINI_API_KEY", os.getenv("MENTORIA_GEMINI_API_KEY", "")
        ).strip()
        self.gemini_model = (
            os.getenv("MENTORIA_GEMINI_MODEL", "gemini-1.5-flash").strip()
            or "gemini-1.5-flash"
        )
        self.gemini_timeout = float(os.getenv("MENTORIA_GEMINI_TIMEOUT", "30"))
        self._gemini_model_instance = None

        if genai is not None and self.gemini_api_key:
            try:
                genai.configure(api_key=self.gemini_api_key)
                self._gemini_model_instance = genai.GenerativeModel(self.gemini_model)
            except Exception as exc:
                logger.warning("Gemini client initialization failed: %s", exc)
                self._gemini_model_instance = None

    def clean_text(self, text: str) -> str:
        return _clean_llm_text(text)

    def ollama_text(
        self, prompt: str, timeout: Optional[float] = None
    ) -> Optional[str]:
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
        }
        effective_timeout = float(
            timeout if timeout is not None else self.ollama_timeout
        )

        try:
            response = requests.post(
                self.ollama_url,
                json=payload,
                timeout=effective_timeout,
            )
            response.raise_for_status()
            body = response.json()
            text = self.clean_text(str(body.get("response") or ""))
            if not text:
                logger.debug("Ollama returned empty response for model: %s", self.model)
                return None
            return text
        except requests.exceptions.ConnectionError as exc:
            logger.debug(
                "Ollama connection failed (is Ollama running at %s?): %s",
                self.ollama_url,
                exc,
            )
            return None
        except requests.exceptions.Timeout:
            logger.debug("Ollama timeout after %.1f seconds", effective_timeout)
            return None
        except Exception as exc:
            logger.debug(
                "Ollama request failed (model: %s, error: %s)", self.model, exc
            )
            return None

    def chat_json(self, prompt: str) -> Optional[Dict[str, Any]]:
        raw = self.ollama_text(prompt)
        if not raw:
            return None
        return _extract_json_object(raw)

    def gemini_text(self, prompt: str) -> Optional[str]:
        if not self._gemini_model_instance:
            logger.debug("Gemini client is not configured")
            return None
        try:
            response = self._gemini_model_instance.generate_content(
                prompt,
                generation_config={
                    "temperature": 0.2,
                    "response_mime_type": "application/json",
                },
                request_options={"timeout": self.gemini_timeout},
            )
            text = self.clean_text(getattr(response, "text", "") or "")
            return text or None
        except Exception as exc:
            logger.debug("Gemini request failed: %s", exc)
            return None
