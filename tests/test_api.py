import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, Mock


@pytest.fixture
def mock_env(monkeypatch, tmp_path):
    """Set up test environment"""
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-key")
    rules_file = tmp_path / "rules.md"
    rules_file.write_text("# Test Rules")
    monkeypatch.setenv("SYSTEM_RULES_PATH", str(rules_file))


def test_health_endpoint_returns_healthy(mock_env):
    """GET /health should return healthy status"""
    from app import app
    client = TestClient(app)

    response = client.get("/health")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "openai" in data
    assert "rules_loaded" in data


def test_root_endpoint_returns_api_info(mock_env):
    """GET / should return API information"""
    from app import app
    client = TestClient(app)

    response = client.get("/")

    assert response.status_code == 200
    data = response.json()
    assert "name" in data
    assert "version" in data


def test_zone_endpoint_requires_json_body(mock_env):
    """POST /zone should validate request body"""
    from app import app
    client = TestClient(app)

    mock_result = {
        "report_markdown": "# Zone 1",
        "summary": {"brand": "Unknown", "zone": "1"}
    }

    with patch("app.openai_service.generate_zone_report", return_value=mock_result):
        response = client.post("/zone", json={})

    # Should accept empty dict (Assessment allows any keys)
    assert response.status_code == 200


def test_zone_endpoint_returns_report_and_summary(mock_env):
    """POST /zone should return markdown report and summary"""
    from app import app
    client = TestClient(app)

    mock_result = {
        "report_markdown": "# Zone 1\nReport content",
        "summary": {"brand": "Test", "zone": "1"}
    }

    with patch("app.openai_service.generate_zone_report", return_value=mock_result):
        response = client.post("/zone", json={"brand": "Test Brand"})

    assert response.status_code == 200
    data = response.json()
    assert "report_markdown" in data
    assert "summary" in data
    assert data["summary"]["brand"] == "Test"


def test_zone_endpoint_handles_openai_errors(mock_env):
    """POST /zone should return 503 on OpenAI service errors"""
    from app import app
    from services.openai_service import OpenAIServiceError
    client = TestClient(app)

    with patch("app.openai_service.generate_zone_report", side_effect=OpenAIServiceError("API failed")):
        response = client.post("/zone", json={"brand": "Test"})

    assert response.status_code == 503
    assert "OpenAI service unavailable" in response.json()["detail"]
