import pytest
from services.openai_service import _extract_summary


def test_extract_summary_with_valid_json():
    """Should extract JSON from properly formatted markdown"""
    markdown = """# Zone 1 — Full Masterbrand Integration

**CONCLUSION:** Integration recommended.

```json
{
  "brand": "TestBrand",
  "zone": "1",
  "zone_name": "Full Masterbrand Integration",
  "subzone": "A",
  "confidence": 90,
  "drivers": ["driver1", "driver2"],
  "conflicts": [],
  "risks": ["risk1"],
  "next_steps": ["step1", "step2"]
}
```

Additional text.
"""

    result = _extract_summary(markdown)

    assert result["brand"] == "TestBrand"
    assert result["zone"] == "1"
    assert result["confidence"] == 90
    assert len(result["drivers"]) == 2
    assert len(result["next_steps"]) == 2


def test_extract_summary_with_whitespace_in_fence():
    """Should handle extra whitespace around JSON fence"""
    markdown = """
Some content

```json

{
  "brand": "Test",
  "zone": "3"
}

```

More content
"""

    result = _extract_summary(markdown)

    assert result["brand"] == "Test"
    assert result["zone"] == "3"


def test_extract_summary_returns_empty_dict_when_no_json():
    """Should return empty dict when no JSON fence found"""
    markdown = "# Report\nNo JSON here"

    result = _extract_summary(markdown)

    assert result == {}


def test_extract_summary_returns_empty_dict_on_malformed_json():
    """Should return empty dict when JSON is malformed"""
    markdown = """
```json
{
  "brand": "Test"
  "zone": "missing comma"
}
```
"""

    result = _extract_summary(markdown)

    assert result == {}


def test_extract_summary_handles_multiple_json_blocks():
    """Should extract first JSON block when multiple present"""
    markdown = """
```json
{"brand": "First", "zone": "1"}
```

```json
{"brand": "Second", "zone": "2"}
```
"""

    result = _extract_summary(markdown)

    # Should get first block
    assert result["brand"] == "First"
    assert result["zone"] == "1"
