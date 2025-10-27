import pytest
from unittest.mock import Mock, patch, MagicMock
from services.openai_service import OpenAIService, OpenAIServiceError
from config import Config


@pytest.fixture
def mock_config(monkeypatch, tmp_path):
    """Create mock config for testing"""
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-key")
    rules_file = tmp_path / "rules.md"
    rules_file.write_text("# Test Rules")
    monkeypatch.setenv("SYSTEM_RULES_PATH", str(rules_file))
    return Config()


def test_openai_service_initializes_with_config(mock_config):
    """OpenAIService should initialize with config"""
    service = OpenAIService(mock_config)

    assert service.config == mock_config
    assert service.client is not None


def test_generate_zone_report_success(mock_config):
    """generate_zone_report should return markdown and summary on success"""
    service = OpenAIService(mock_config)

    mock_response = Mock()
    mock_response.output_text = """# Zone 1 — Full Masterbrand Integration (Recommended)

**CONCLUSION:** Brand should integrate.

```json
{
  "brand": "Test Brand",
  "zone": "1",
  "zone_name": "Full Masterbrand Integration",
  "subzone": "A",
  "confidence": 85,
  "drivers": ["driver1"],
  "conflicts": [],
  "risks": ["risk1"],
  "next_steps": ["step1"]
}
```
"""

    with patch.object(service.client.responses, 'create', return_value=mock_response):
        result = service.generate_zone_report({"brand": "Test"})

    assert "Zone 1" in result["report_markdown"]
    assert result["summary"]["brand"] == "Test Brand"
    assert result["summary"]["zone"] == "1"


def test_generate_zone_report_retries_on_timeout(mock_config):
    """generate_zone_report should retry on timeout errors"""
    service = OpenAIService(mock_config)

    # First two calls timeout, third succeeds
    mock_response = Mock()
    mock_response.output_text = "# Zone 1\n```json\n{\"brand\":\"Test\",\"zone\":\"1\",\"zone_name\":\"Full Masterbrand Integration\",\"subzone\":\"A\",\"confidence\":80,\"drivers\":[],\"conflicts\":[],\"risks\":[],\"next_steps\":[]}\n```"

    with patch.object(service.client.responses, 'create') as mock_create:
        from openai import APITimeoutError
        mock_create.side_effect = [
            APITimeoutError("Timeout"),
            APITimeoutError("Timeout"),
            mock_response
        ]

        result = service.generate_zone_report({"brand": "Test"})

    assert mock_create.call_count == 3
    assert "Zone 1" in result["report_markdown"]


def test_generate_zone_report_fails_after_max_retries(mock_config):
    """generate_zone_report should raise error after max retries"""
    service = OpenAIService(mock_config)

    with patch.object(service.client.responses, 'create') as mock_create:
        from openai import APITimeoutError
        mock_create.side_effect = APITimeoutError("Timeout")

        with pytest.raises(OpenAIServiceError, match="OpenAI API call failed"):
            service.generate_zone_report({"brand": "Test"})

    assert mock_create.call_count == 3


def test_extract_summary_parses_json_from_markdown():
    """_extract_summary should parse JSON from markdown code fence"""
    from services.openai_service import _extract_summary

    markdown = """
# Report

Some text

```json
{
  "brand": "Test",
  "zone": "3"
}
```

More text
"""

    summary = _extract_summary(markdown)

    assert summary["brand"] == "Test"
    assert summary["zone"] == "3"


def test_extract_summary_returns_empty_dict_on_invalid_json():
    """_extract_summary should return empty dict if JSON invalid"""
    from services.openai_service import _extract_summary

    markdown = "No JSON here"
    summary = _extract_summary(markdown)

    assert summary == {}
