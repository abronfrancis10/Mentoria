from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_read_root():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"status": "Mentoria backend running"}


def test_resume_upload_method_not_allowed():
    # This endpoint expects POST, so GET should be 405
    response = client.get("/api/resume/upload")
    assert response.status_code == 405
