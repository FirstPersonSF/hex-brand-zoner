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


def _validate_zone_assignment(assessment: Dict[str, Any], summary: Dict[str, Any], brand_name: str) -> None:
    """Validate zone assignment against assessment data and log warnings

    Args:
        assessment: Brand architecture assessment data
        summary: Parsed summary from AI response
        brand_name: Brand name for logging
    """
    zone = summary.get("zone", "")
    subzone = summary.get("subzone", "")

    # Check Zone 5 gating condition
    zone5_data = assessment.get("zone5", {})
    if zone5_data.get("active_restriction_preventing_hex"):
        if zone != "5":
            logger.error(f"❌ [{brand_name}] Z5 Q1 gating condition (legal restriction) present but assigned Zone {zone}")

    # Check Zone 4 triggers
    zone4_data = assessment.get("zone4", {})
    z4_triggers = [
        ("hex_branding_reduces_trust", "Q2: Hex branding reduces trust"),
        ("hex_link_creates_risk", "Q3: Hex link creates risk"),
        ("stakeholders_object_elimination", "Q8: Stakeholders object to elimination"),
        ("rebrand_invalidates_contracts", "Q9: Contracts would be invalidated")
    ]

    z4_trigger_count = sum(1 for key, _ in z4_triggers if zone4_data.get(key))
    if z4_trigger_count > 0 and zone != "4":
        triggered = [desc for key, desc in z4_triggers if zone4_data.get(key)]
        logger.warning(f"⚠️ [{brand_name}] {z4_trigger_count} Zone 4 trigger(s) present but assigned Zone {zone}: {', '.join(triggered)}")

    # Check Zone 3A indicators vs assignment
    if zone == "3":
        zone3_data = assessment.get("zone3", {})
        z3_confidence = zone3_data.get("z3_confidence_fallback", {})

        z3a_indicators = {
            "removal_causes_attrition": "Q8a: Removal causes attrition",
            "removal_risk_in_key_markets": "Removal risk in key markets",
            "transition_complexity_gt12mo": "Q8b: Complex transition >12mo"
        }

        z3a_score = sum(1 for key in z3a_indicators if zone3_data.get(key))

        # Additional Z3A indicators from confidence section
        if z3_confidence.get("generates_demand_via_own_equity"):
            z3a_score += 1
        if zone3_data.get("higher_awareness_than_hex"):
            z3a_score += 1

        # Zone 1 revenue indicator
        zone1_data = assessment.get("zone1", {})
        if zone1_data.get("pct_of_division_revenue") == "20-70":
            z3a_score += 1

        if subzone == "A" and z3a_score < 2:
            logger.warning(f"⚠️ [{brand_name}] Zone 3A assigned but only {z3a_score} strong Z3A indicators found")
        elif subzone == "B" and z3a_score >= 3:
            logger.warning(f"⚠️ [{brand_name}] Zone 3B assigned but {z3a_score} Z3A indicators present (may warrant 3A)")
        elif subzone == "C" and zone3_data.get("independent_marketing_budget"):
            logger.warning(f"⚠️ [{brand_name}] Zone 3C assigned but brand has independent marketing budget (usually Z3A/3B)")

    # Check Zone 1 indicators
    if zone == "1":
        zone1_data = assessment.get("zone1", {})
        if zone1_data.get("pct_of_division_revenue") in ["20-70", "> 70"]:
            logger.warning(f"⚠️ [{brand_name}] Zone 1 assigned but revenue contribution is {zone1_data.get('pct_of_division_revenue')} (usually Z3A or Z2B)")

    logger.info(f"✅ [{brand_name}] Validation complete: Zone {zone}{subzone or ''}")


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
1) H1 line: "# Zone X[Subzone] — [Zone Name] (Recommended)" (e.g., "# Zone 3A — Endorsed Brand Architecture (Recommended)")
2) **CONCLUSION:** ...
3) Confidence block with numeric score format (see below)
4) **SCORING BREAKDOWN:** Show all zone scores with question tallies (see format below)
5) Zone-Specific Assessment
6) Strategic Recommendations
7) Risk Analysis & Mitigation
8) Next Steps & Action Items
9) Machine-Readable Summary as fenced ```json with exact keys

Confidence Format:
**Confidence: X/100**

- Evidence: Y/40 (strength and clarity of data provided)
- Completeness: Z/30 (how much critical data is present)
- Conflict Resolution: W/30 (inverse of contradictions - lower conflicts = higher score)

Example:
**Confidence: 85/100**

- Evidence: 35/40 (Strong data on removal risk, transition complexity, and market presence)
- Completeness: 28/30 (Most critical questions answered, minor gaps in legacy data)
- Conflict Resolution: 22/30 (Some tension between independence signals and integration plan)

Scoring Breakdown Format:
**SCORING BREAKDOWN**

Main Zones:
- Zone 1: X points (list top 3-5 contributing questions)
- Zone 3: X points ← WINNER (list top 3-5 contributing questions)
- Zone 4: X points (list top 3-5 contributing questions)
- Zone 5: X points (list top 3-5 contributing questions)

[If Zone 3 wins, also show:]
Zone 3 Sub-zones:
- 3A (Lockup): X points ← WINNER (list top 3 indicators)
- 3B (Sub-brand): X points (list top 3 indicators)
- 3C (Integrated): X points (list top 3 indicators)

Winner Margin: X points ahead of second place

Example:
Main Zones:
- Zone 1: 8 points (Q1 revenue <20%, Q5 no confusion)
- Zone 3: 22 points ← WINNER (Q8a removal risk, Q8b complex transition, revenue 20-70%)
- Zone 4: 6 points (Q1 awareness 50-70%)
- Zone 5: 3 points (Q2 no integration plan)

Zone 3 Sub-zones:
- 3A: 16 points ← WINNER (removal risk, transition >12mo, revenue contribution)
- 3B: 8 points (some equity signals)
- 3C: 2 points (minimal embedding)

Winner Margin: 14 points ahead of Zone 1

Precedence Rules (CRITICAL - Follow Exactly):

STEP 1 - Check GATING conditions (immediate assignment):
- Z5 Q1: Legal/compliance restriction = Yes → FORCE Zone 5 (stop evaluation)
- Z4: High-risk independence criteria met → FORCE Zone 4 (per rules file)

STEP 2 - If no gates triggered, use SCORING (accumulative):
- Each question contributes points to one or more zones (Z1, Z3, Z4, Z5)
- Questions can add points to MULTIPLE zones simultaneously
- Examples:
  * Z5 Q2 (No integration plan): No = +3 Z5 | Yes = +1 Z1 AND +1 Z3
  * Z5 Q3 (Planned sale): Yes = +3 Z5 | No = +1 Z1 AND +1 Z3
  * Z5 Q4 (Integration forecast): No = +3 Z5 | Yes = +2 Z1 AND +2 Z3
- Tally ALL points across ALL questions for each zone
- Highest total zone score wins

STEP 3 - Determine SUB-ZONE (for Zone 3 only):
If Zone 3 wins, determine A/B/C based on questions that specify sub-zones:

Zone 3A (Lockup) indicators:
- High removal risk (Q8a: removal causes attrition/confusion)
- Complex transition >12mo (Q8b: multi-region, partner/OEM complexity)
- Brand outperforms Hexagon in metrics (Q5: +2 Z3A)
- Top 2 ranked but endorsable (Z4 Q10: No = +2 Z3A)
- Revenue 20-70% of division (Z1 Q1: +2 Z3A)
- Cannot easily integrate (Z3 Confidence Q7: No)
- Strong independent equity (Q14: ≥40% awareness 3+ years)

Zone 3B (Sub-brand) indicators:
- Part of Hexagon platform/ecosystem (Q2: +2 Z3B)
- Plan to retain name only (Z1 Q2B: +2 Z3B)
- Easier transition <12mo (Q8b: No = +2 Z3B)
- Some brand equity but not dominant
- Product/experience loyalty (Q36: NPS-based)

Zone 3C (Integrated Product) indicators:
- Embedded in technical stacks/user flows
- No independent marketing budget (Q10: No = +2 Z3C)
- Primarily product/service name not brand identity

Tally sub-zone specific points. Highest sub-zone score determines final placement.
Report as "Zone 3A", "Zone 3B", or "Zone 3C" in both H1 and JSON "subzone" field.

IMPORTANT: Do NOT assign Zone 5 unless Z5 Q1 gates it OR Z5 has the highest cumulative score.
Missing integration plans alone does NOT force Zone 5 - it only adds +3 points to Z5 scoring.

Quick Scoring Reference (Key Questions):

ZONE 4 (High-Stakes Independence):
- Q2 (Hex branding reduces trust): Yes = +2 Z4
- Q3 (Hex link creates risk): Yes = +3 Z4
- Q7 (Values incompatible): Yes = +2 Z4
- Q8 (Stakeholders object to elimination): Yes = Gate Z4
- Q9 (Contracts invalidated): Yes = Gate Z4
- Q10 (Top 2, endorsement weakens): Yes = +2 Z4 | No = +2 Z3A

ZONE 5 (Legal/Transitional):
- Q1 (Legal restriction): Yes = GATE Z5 (forces Zone 5)
- Q2 (No integration plan): No = +3 Z5 | Yes = +1 Z1, +1 Z3
- Q3 (Planned divestiture): Yes = +3 Z5 | No = +1 Z1, +1 Z3
- Q4 (No integration forecast): No = +3 Z5 | Yes = +2 Z1, +2 Z3
- Q5 (Pilot/POC stage): Yes = +2 Z5
- Q6 (Time-bound separation): Yes = +3 Z5 | No = +1 Z1, +1 Z3

ZONE 1 (Masterbrand Integration):
- Q1 (Revenue): <20% = +3 Z1 | 20-70% = +2 Z3A
- Q2 (Embedding): Partially = moderate | Fully embedded = +Z1 signals
- Q5 (Customer confusion): Yes = -1 Z1
- Q14 (Removing strengthens clarity): Yes = +2 Z1

ZONE 3 (Endorsed):
- Q1 (≥20% awareness): Yes = +2 Z3
- Q2 (Higher awareness than Hex): Yes = +2 Z3
- Q3 (Removal causes attrition): Yes = +2 Z3A/Z3B
- Q5 (Outperforms Hex metrics): Yes = +2 Z3A
- Q8a (Removal creates risk): Yes = +2 Z3A/Z3B | No = +1 Z1
- Q8b (Transition >12mo): Yes = +1 Z3A | No = +2 Z3B
- Q10 (Independent marketing): Yes = +2 Z3A | No = +2 Z3C
- Confidence Q10 (Generates demand independently): Yes = +3 Z3A

Confidence Calculation (REQUIRED - Must show numeric breakdown):
Total = [Evidence 0–40] + [Completeness 0–30] + [Conflict Resolution 0–30] = N/100

Evidence (0-40): Strength and clarity of data
- 30-40: Strong, specific evidence with citations
- 20-29: Moderate evidence, some gaps
- 10-19: Weak or conflicting evidence
- 0-9: Minimal evidence

Completeness (0-30): Critical data present
- 25-30: All key questions answered
- 15-24: Most questions answered, minor gaps
- 5-14: Significant data gaps
- 0-4: Severely incomplete

Conflict Resolution (0-30): Consistency of signals (inverse of conflicts)
- 25-30: Clear, consistent signals
- 15-24: Minor contradictions
- 5-14: Significant conflicts
- 0-4: Highly contradictory

ALWAYS show numeric breakdown. If thin data, label as "Provisional" but still provide N/100 score.

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
        # Extract brand name for logging
        brand_name = assessment.get("brand", "Unknown")
        logger.info(f"Zone request for brand: {brand_name}")

        user_msg = (
            "ASSESSMENT JSON:\n" +
            json.dumps(assessment, ensure_ascii=False, indent=2) +
            "\n\nFollow all formatting + precedence rules exactly."
        )

        # Track response time
        start_time = time.time()

        # Retry logic
        for attempt in range(self.config.openai_max_retries):
            try:
                logger.info(f"Calling OpenAI API (attempt {attempt + 1}/{self.config.openai_max_retries})")

                # Debug logging - show what's being sent (only in DEBUG mode)
                logger.debug(f"System prompt length: {len(self.system_prompt)} chars")
                logger.debug(f"Developer prompt length: {len(self.developer_prompt)} chars")
                logger.debug(f"Assessment JSON length: {len(user_msg)} chars")
                logger.debug(f"Model: {self.config.openai_model}, Temperature: {self.config.temperature}")

                response = self.client.chat.completions.create(
                    model=self.config.openai_model,
                    messages=[
                        {"role": "system", "content": self.system_prompt},
                        {"role": "developer", "content": self.developer_prompt},
                        {"role": "user", "content": user_msg},
                    ],
                    temperature=self.config.temperature
                )

                markdown = response.choices[0].message.content
                summary = _extract_summary(markdown)

                # Calculate response time
                response_time = time.time() - start_time

                # Log detailed results
                zone = summary.get("zone", "unknown")
                zone_name = summary.get("zone_name", "unknown")
                confidence = summary.get("confidence", 0)

                logger.info(f"OpenAI response received in {response_time:.2f}s")
                logger.info(f"Recommended zone: {zone} ({zone_name}) with {confidence}% confidence")
                logger.info("Successfully generated zone report")

                # Validate zone assignment against assessment data
                _validate_zone_assignment(assessment, summary, brand_name)

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
