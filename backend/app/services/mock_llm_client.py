import json
import logging
from typing import Optional, Any

logger = logging.getLogger(__name__)

class MockLLMClient:
    """
    A mock implementation of AsyncLLMClient for testing without API keys or Ollama.
    It returns static responses based on keywords in the prompt.
    """
    def __init__(self):
        self.gemini_client = None
        self.ollama_model = "mock-model"
        self.ollama_model_question = "mock-model-q"
        self.ollama_model_evaluation = "mock-model-e"
        self.ollama_timeout = 30.0
        self.gemini_api_key = "mock-key"
        self.gemini_model = "mock-gemini"
        self.gemini_timeout = 30.0
        logger.info("MockLLMClient initialized (Offline Mode)")

    async def generate_ollama(self, prompt: str, model: Optional[str] = None) -> Optional[str]:
        return await self.generate_gemini(prompt)

    async def generate_gemini(self, prompt: str) -> Optional[str]:
        """Returns mock responses based on the prompt content."""
        prompt_lower = prompt.lower()
        
        # 1. Mock Question Generation
        if "generate" in prompt_lower and "question" in prompt_lower:
            if "bundle" in prompt_lower:
                return json.dumps({
                    "technical": ["MOCK: Explain the event loop in Node.js."],
                    "behavioral": ["MOCK: Tell me about a time you resolved a conflict."],
                    "scenario": ["MOCK: The server is down and you're the only one on call. What do you do?"]
                })
            return json.dumps({
                "question": "MOCK: How do you handle state management in a large-scale React application?",
                "expected_answer": ["Redux", "Context API", "Zustand", "Atomic state"],
                "difficulty": "medium",
                "category": "technical"
            })

        # 3. Mock Evaluation
        if "evaluate" in prompt_lower and "answer" in prompt_lower:
            # Check for a 'weak' answer in the prompt to simulate a bad score
            if "i don't know" in prompt_lower or "performance?" in prompt_lower:
                return json.dumps({
                    "scores": {"correctness": 3, "completeness": 2, "technical_depth": 1, "clarity": 5},
                    "overall_score": 3,
                    "missing_points": ["Technical depth", "Specific examples"],
                    "strengths": ["Clear speech"],
                    "feedback": "Try to provide more technical detail."
                })
            return json.dumps({
                "scores": {"correctness": 9, "completeness": 8, "technical_depth": 9, "clarity": 9},
                "overall_score": 9,
                "missing_points": ["Minor edge cases"],
                "strengths": ["Excellent technical depth", "Structured answer"],
                "feedback": "Strong answer with good real-world context."
            })

        # 4. Mock Next Step
        if "next" in prompt_lower and "difficulty" in prompt_lower:
            return json.dumps({
                "next_difficulty": "hard",
                "ui_action": "SUBMIT_AND_LOAD_NEXT",
                "reason": "Previous scores were high."
            })

        return "MOCK: Default response for unknown prompt."

    async def generate_json(self, prompt: str) -> Optional[Any]:
        res = await self.generate_gemini(prompt)
        if res:
            try:
                return json.loads(res)
            except Exception:
                return None
        return None

# To use this mock, you would temporarily swap the singleton in async_llm_client.py
# or use a monkeypatch in your tests.
