import pytest
from fastapi.testclient import TestClient
from pathlib import Path
import json


@pytest.fixture
def mock_env(monkeypatch):
    """Set up test environment with real rules file"""
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-key")
    # Use actual rules file from project
    rules_path = Path(__file__).parent.parent / "rules" / "HEX 5112 - Brand Architecture - Full Set of Questions & Logic Scoring v009.md"
    if rules_path.exists():
        monkeypatch.setenv("SYSTEM_RULES_PATH", str(rules_path))


@pytest.fixture
def sample_assessment():
    """Load sample assessment from samples directory"""
    sample_path = Path(__file__).parent.parent / "samples" / "novatel_assessment.json"
    with open(sample_path, "r") as f:
        return json.load(f)


def test_zone_endpoint_with_sample_assessment(mock_env, sample_assessment):
    """POST /zone should process actual sample assessment"""
    from app import app
    from unittest.mock import patch, Mock
    client = TestClient(app)

    # Mock OpenAI response with realistic data
    mock_choice = Mock()
    mock_choice.message.content = """# Zone 1 — Full Masterbrand Integration (Recommended)

**CONCLUSION:** Based on the assessment data, NovAtel should pursue full integration into the Hexagon masterbrand.

**Confidence: 75/100**
- Evidence strength: 30/40
- Data completeness: 25/30
- Conflict resolution: 20/30

**Zone-Specific Assessment**
The brand shows strong indicators for masterbrand integration with limited market awareness outside current territories.

**Strategic Recommendations**
- Begin phased integration over 12-month period
- Leverage Hexagon's positioning in autonomy markets

**Risk Analysis & Mitigation**
- Monitor customer awareness during transition
- Address potential confusion in legacy markets

**Next Steps & Action Items**
1. Develop detailed integration roadmap
2. Communicate changes to key stakeholders
3. Update digital presence and materials

**Machine-Readable Summary**
```json
{
  "brand": "NovAtel",
  "zone": "1",
  "zone_name": "Full Masterbrand Integration",
  "subzone": "A",
  "confidence": 75,
  "drivers": ["Low independent awareness", "Partially embedded"],
  "conflicts": ["Legacy presence in some regions"],
  "risks": ["Customer confusion during transition"],
  "next_steps": ["Develop integration roadmap", "Stakeholder communication"]
}
```
"""
    mock_response = Mock()
    mock_response.choices = [mock_choice]

    with patch("app.openai_service.client.chat.completions.create", return_value=mock_response):
        response = client.post("/zone", json=sample_assessment)

    assert response.status_code == 200
    data = response.json()

    # Verify structure
    assert "report_markdown" in data
    assert "summary" in data

    # Verify summary content
    summary = data["summary"]
    assert summary["brand"] == "NovAtel"
    assert summary["zone"] in ["1", "3", "4", "5"]
    assert "zone_name" in summary
    assert "confidence" in summary
    assert isinstance(summary["drivers"], list)
    assert isinstance(summary["next_steps"], list)


def test_health_check_with_real_config(mock_env):
    """GET /health should return accurate status with real config"""
    from app import app
    client = TestClient(app)

    response = client.get("/health")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["openai"] == "configured"
    assert data["model"] == "gpt-4o"
