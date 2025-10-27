import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def mock_env(monkeypatch, tmp_path):
    """Set up test environment"""
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-key")
    rules_file = tmp_path / "rules.md"
    rules_file.write_text("# Test Rules")
    monkeypatch.setenv("SYSTEM_RULES_PATH", str(rules_file))


def test_zone_accepts_empty_assessment(mock_env):
    """POST /zone should accept empty assessment dict"""
    from app import app
    from unittest.mock import patch
    client = TestClient(app)

    mock_result = {
        "report_markdown": "# Zone 1",
        "summary": {"brand": "Unknown", "zone": "1", "zone_name": "Full Masterbrand Integration",
                   "subzone": "A", "confidence": 50, "drivers": [], "conflicts": [],
                   "risks": [], "next_steps": []}
    }

    with patch("app.openai_service.generate_zone_report", return_value=mock_result):
        response = client.post("/zone", json={})

    assert response.status_code == 200


def test_zone_accepts_complex_nested_assessment(mock_env):
    """POST /zone should accept deeply nested assessment structures"""
    from app import app
    from unittest.mock import patch
    client = TestClient(app)

    complex_assessment = {
        "brand": "Test",
        "zone1": {"field": "value", "nested": {"deep": "data"}},
        "zone2": {"array": [1, 2, 3]},
        "metadata": {"user": "test", "timestamp": "2025-10-26"}
    }

    mock_result = {
        "report_markdown": "# Zone 3",
        "summary": {"brand": "Test", "zone": "3", "zone_name": "Endorsed Brand",
                   "subzone": "B", "confidence": 75, "drivers": [], "conflicts": [],
                   "risks": [], "next_steps": []}
    }

    with patch("app.openai_service.generate_zone_report", return_value=mock_result):
        response = client.post("/zone", json=complex_assessment)

    assert response.status_code == 200


def test_zone_rejects_non_json_body(mock_env):
    """POST /zone should reject non-JSON request bodies"""
    from app import app
    client = TestClient(app)

    response = client.post("/zone", data="not json")

    assert response.status_code == 422


def test_zone_rejects_json_array(mock_env):
    """POST /zone should reject JSON array (expects object)"""
    from app import app
    client = TestClient(app)

    response = client.post("/zone", json=["array", "not", "object"])

    assert response.status_code == 422
