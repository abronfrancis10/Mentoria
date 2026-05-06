from fastapi.testclient import TestClient
import os
import sys

# Ensure backend is in path
sys.path.append(os.path.join(os.getcwd(), 'backend'))

# Force offline mode for all imports
os.environ["OFFLINE_MODE"] = "true"

import app.services.async_llm_client
from app.services.mock_llm_client import MockLLMClient

# Force the mock client into the service
app.services.async_llm_client.async_llm_client = MockLLMClient()

from app.main import app  # noqa: E402
client = TestClient(app)

def test_generate_questions_mock():
    """Verify that question generation works in offline mode."""
    payload = {
        "role": "Backend Developer",
        "skills": ["Python", "FastAPI"],
        "difficulty": "medium"
    }
    response = client.post("/api/questions/generate", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "questions" in data
    assert "technical" in data["questions"]
    assert "behavioral" in data["questions"]
    assert "scenario" in data["questions"]
    # Check if mock text is present
    assert "MOCK:" in data["questions"]["technical"][0]

def test_evaluate_answer_mock():
    """Verify that answer evaluation works in offline mode."""
    payload = {
        "role": "Backend Developer",
        "question": "MOCK: Explain the event loop in Node.js.",
        "answer": "I don't know much about it, maybe something about performance?",
        "difficulty": "medium"
    }
    response = client.post("/api/evaluation/evaluate", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "score" in data
    assert data["score"] <= 4.0  # Should be low because of keywords in mock
    # The mock returns feedback as a direct string in communication_feedback
    assert "technical detail" in data["communication_feedback"].lower()
