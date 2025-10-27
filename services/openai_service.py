import json
import re
import time
from typing import Any, Dict
from openai import OpenAI, APITimeoutError, APIError
from config import Config
from utils.logging_config import get_logger

logger = get_logger(__name__)


class OpenAIServiceError(Exception):
    """Raised when OpenAI service encounters an error"""
    pass


def _extract_summary(markdown: str) -> Dict[str, Any]:
    """Extract JSON summary from markdown code fence

    Args:
        markdown: Markdown text containing ```json code fence

    Returns:
        Parsed JSON dict or empty dict if not found/invalid
    """
    match = re.search(r"```json\s*(\{.*?\})\s*```", markdown, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            logger.warning("Failed to parse JSON from markdown")
            return {}
    return {}


class OpenAIService:
    """Service for interacting with OpenAI API"""

    MACHINE_JSON_SCHEMA = {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "brand": {"type": "string"},
            "zone": {"type": "string", "enum": ["1", "3", "4", "5"]},
            "zone_name": {"type": "string", "enum": [
                "Full Masterbrand Integration", "Endorsed Brand",
                "High-Stakes Independence", "Legal/Accounting/Integration Hold"
            ]},
            "subzone": {"type": "string"},
            "confidence": {"type": "integer", "minimum": 0, "maximum": 100},
            "drivers": {"type": "array", "items": {"type": "string"}},
            "conflicts": {"type": "array", "items": {"type": "string"}},
            "risks": {"type": "array", "items": {"type": "string"}},
            "next_steps": {"type": "array", "items": {"type": "string"}}
        },
        "required": ["brand", "zone", "zone_name", "subzone", "confidence",
                     "drivers", "conflicts", "risks", "next_steps"]
    }

    def __init__(self, config: Config):
        """Initialize OpenAI service

        Args:
            config: Application configuration
        """
        self.config = config
        self.client = OpenAI(api_key=config.openai_api_key)

        # Build system prompt with rules
        rules_text = config.load_rules_text()
        self.system_prompt = f"""You are a strict brand-architecture adjudicator.
Apply these rules verbatim. If the rules file is present, it overrides ambiguities.

=== RULES FILE (if provided) ===
{rules_text}
=== END RULES FILE ===
"""

        self.developer_prompt = """You MUST output, in order:
1) H1 line: "# Zone X — [Zone Name] (Recommended)"
2) **CONCLUSION:** ...
3) Confidence block with exact two lines + 1–3 bullets
4) Zone-Specific Assessment
5) Strategic Recommendations
6) Risk Analysis & Mitigation
7) Next Steps & Action Items
8) Machine-Readable Summary as fenced ```json with exact keys

Precedence Rules:
- If ANY Zone 5 trigger present → Zone 5.
- Else if Zone 4 gating criteria met → Zone 4.
- Else decide Zone 1 vs Zone 3 using tie-breakers.

Confidence = [Evidence 0–40] + [Completeness 0–30] + [Conflict (inverse) 0–30] = N/100.
If thin data, produce a Provisional score.

Formatting:
- Anchors: zone-recommendation, conclusion, confidence, zone-assessment, strategy, risks, next-steps, summary-json.
- ≤120 words per section; bullets OK; no extra sections.
- Cite evidence with (Q#) or (Not provided in assessment)."""

    def generate_zone_report(self, assessment: Dict[str, Any]) -> Dict[str, Any]:
        """Generate zone recommendation report from assessment

        Args:
            assessment: Brand architecture assessment data

        Returns:
            Dict with 'report_markdown' and 'summary' keys

        Raises:
            OpenAIServiceError: If API call fails after retries
        """
        user_msg = (
            "ASSESSMENT JSON:\n" +
            json.dumps(assessment, ensure_ascii=False, indent=2) +
            "\n\nFollow all formatting + precedence rules exactly."
        )

        # Retry logic
        for attempt in range(self.config.openai_max_retries):
            try:
                logger.info(f"Calling OpenAI API (attempt {attempt + 1}/{self.config.openai_max_retries})")

                response = self.client.responses.create(
                    model=self.config.openai_model,
                    input=[
                        {"role": "system", "content": self.system_prompt},
                        {"role": "developer", "content": self.developer_prompt},
                        {"role": "user", "content": user_msg},
                    ],
                    text={
                        "format": {
                            "type": "json_schema",
                            "schema": self.MACHINE_JSON_SCHEMA
                        }
                    },
                    temperature=self.config.temperature
                )

                markdown = response.output_text
                summary = _extract_summary(markdown)

                logger.info("Successfully generated zone report")
                return {
                    "report_markdown": markdown,
                    "summary": summary
                }

            except (APITimeoutError, APIError) as e:
                logger.warning(f"OpenAI API error (attempt {attempt + 1}): {e}")

                if attempt < self.config.openai_max_retries - 1:
                    # Exponential backoff
                    sleep_time = 2 ** attempt
                    logger.info(f"Retrying in {sleep_time}s...")
                    time.sleep(sleep_time)
                else:
                    raise OpenAIServiceError(
                        f"OpenAI API call failed after {self.config.openai_max_retries} attempts: {e}"
                    )

        raise OpenAIServiceError("Unexpected error in retry logic")
