# Prompt Architecture & System Improvements

## Overview

The Brand Zoning API uses a sophisticated prompt engineering approach to convert brand architecture assessments into zone recommendations. This document explains how the system works, the improvements made, and the reasoning behind the prompt structure.

---

## System Architecture

### High-Level Flow

```
Assessment JSON → OpenAI API → AI Analysis → Zone Recommendation + Scoring Breakdown
                      ↓
                System Prompt (Rules File)
                Developer Prompt (Scoring Logic)
                      ↓
                Post-Processing Validation
                      ↓
                Logs + Response to User
```

### Three-Prompt Strategy

The system uses three distinct prompts, each serving a specific purpose:

#### 1. **System Prompt** (Role & Rules)
```python
self.system_prompt = f"""You are a strict brand-architecture adjudicator.
Apply these rules verbatim. If the rules file is present, it overrides ambiguities.

=== RULES FILE (if provided) ===
{rules_text}
=== END RULES FILE ===
"""
```

**Purpose:**
- Sets the AI's role and authority level
- Injects the complete 1781-line rules document
- Establishes that rules override any conflicting guidance

**Why separate:** System prompts set persistent context across all interactions. By keeping rules here, they're always authoritative.

#### 2. **Developer Prompt** (Format & Scoring Logic)
Contains 5 major sections:

1. **Output Format Requirements**
2. **Scoring Breakdown Format** (with examples)
3. **Precedence Rules** (3-step decision tree)
4. **Sub-Zone Determination** (Zone 3A/3B/3C criteria)
5. **Quick Scoring Reference** (key question lookup table)

**Why separate:** Developer prompts provide technical instructions that complement but don't override the system context.

#### 3. **User Prompt** (Assessment Data)
```python
user_msg = (
    "ASSESSMENT JSON:\n" +
    json.dumps(assessment, ensure_ascii=False, indent=2) +
    "\n\nFollow all formatting + precedence rules exactly."
)
```

**Purpose:**
- Provides the actual assessment data
- Reinforces format requirements
- Keeps data separate from instructions

---

## Chronological Journey of Improvements

### Phase 1: Initial Deployment (Oct 25)
- Basic FastAPI setup
- Single prompt with embedded rules
- No scoring transparency
- Zone assignment based on implicit AI reasoning

**Problem:** Zone 5 being assigned too aggressively, no way to debug why.

### Phase 2: Precedence Logic Fix (Oct 27 - First Fix)
**Issue:** API was treating ANY Zone 5 indicator as forcing Zone 5 assignment.

**Old logic:**
```
- If ANY Zone 5 trigger present → Zone 5
```

**Fixed logic:**
```
STEP 1 - Check GATING conditions:
- Z5 Q1: Legal/compliance restriction = Yes → FORCE Zone 5
- Z4: High-risk independence criteria met → FORCE Zone 4

STEP 2 - If no gates triggered, use SCORING (accumulative):
- Each question contributes points to one or more zones
- Tally ALL points across ALL questions
- Highest total zone score wins
```

**Impact:** NovAtel correctly moved from Zone 5 → Zone 3 (but no subzone specified).

### Phase 3: Subzone Logic Addition (Oct 27 - Second Fix)
**Issue:** Zone 3 brands weren't being classified into 3A (Lockup), 3B (Sub-brand), or 3C (Integrated Product).

**Added STEP 3:**
```
If Zone 3 wins, determine A/B/C based on questions that specify sub-zones:

Zone 3A (Lockup) indicators:
- High removal risk (Q8a: removal causes attrition/confusion)
- Complex transition >12mo (Q8b: multi-region, partner/OEM complexity)
- Brand outperforms Hexagon in metrics (Q5: +2 Z3A)
- Revenue 20-70% of division (Z1 Q1: +2 Z3A)
- Strong independent equity (Q14: ≥40% awareness 3+ years)

Zone 3B (Sub-brand) indicators:
- Part of Hexagon platform/ecosystem (Q2: +2 Z3B)
- Easier transition <12mo (Q8b: No = +2 Z3B)
- Moderate brand equity

Zone 3C (Integrated Product) indicators:
- Embedded in technical stacks/user flows
- No independent marketing budget (Q10: No = +2 Z3C)
```

**Impact:** Zone 3 results now specify 3A, 3B, or 3C.

### Phase 4: Scoring Transparency & Validation (Oct 27 - Third Fix)
**Issue:** No visibility into scoring calculations, no error detection.

**Added three features:**

#### A. Scoring Breakdown Output
Forces AI to show its work in every report:

```markdown
**SCORING BREAKDOWN**

Main Zones:
- Zone 1: 8 points (Q1 revenue <20%, Q5 no confusion)
- Zone 3: 22 points ← WINNER (Q8a removal risk, Q8b complex transition)
- Zone 4: 6 points (Q1 awareness 50-70%)
- Zone 5: 3 points (Q2 no integration plan)

Zone 3 Sub-zones:
- 3A: 16 points ← WINNER (removal risk, transition >12mo)
- 3B: 8 points (some equity signals)
- 3C: 2 points (minimal embedding)

Winner Margin: 14 points ahead of Zone 1
```

#### B. Quick Scoring Reference Table
Added to developer prompt as a lookup table:

```
ZONE 4 (High-Stakes Independence):
- Q2 (Hex branding reduces trust): Yes = +2 Z4
- Q10 (Top 2, endorsement weakens): Yes = +2 Z4 | No = +2 Z3A

ZONE 5 (Legal/Transitional):
- Q1 (Legal restriction): Yes = GATE Z5 (forces Zone 5)
- Q2 (No integration plan): No = +3 Z5 | Yes = +1 Z1, +1 Z3

ZONE 1 (Masterbrand Integration):
- Q1 (Revenue): <20% = +3 Z1 | 20-70% = +2 Z3A

ZONE 3 (Endorsed):
- Q3 (Removal causes attrition): Yes = +2 Z3A/Z3B
- Q8a (Removal creates risk): Yes = +2 Z3A/Z3B | No = +1 Z1
- Q8b (Transition >12mo): Yes = +1 Z3A | No = +2 Z3B
- Q10 (Independent marketing): Yes = +2 Z3A | No = +2 Z3C
```

**Why this helps:**
- AI doesn't need to memorize all 1781 lines
- Quick reference for common patterns
- Self-documenting prompt

#### C. Post-Processing Validation
Python function that validates every zone assignment:

```python
def _validate_zone_assignment(assessment, summary, brand_name):
    """
    Checks:
    1. Zone 5 gating violations
    2. Zone 4 triggers present but not assigned
    3. Zone 3 subzone logic (3A without indicators, etc.)
    4. Zone 1 with high revenue contribution

    Logs warnings/errors with emoji indicators
    """
```

**Example logs:**
```
✅ [NovAtel] Validation complete: Zone 3A
⚠️ [Brand X] Zone 3B assigned but 4 Z3A indicators present (may warrant 3A)
❌ [Brand Y] Z5 Q1 gating condition (legal restriction) present but assigned Zone 3
```

**Impact:**
- Scoring is now auditable
- Errors caught automatically
- Easier debugging
- Improved consistency

---

## Current Prompt Structure

### Developer Prompt Breakdown

```
┌─────────────────────────────────────────────────────┐
│ 1. OUTPUT FORMAT REQUIREMENTS                       │
│    - 9 sections in specific order                   │
│    - H1 format: "Zone 3A — Endorsed Brand"          │
│    - Scoring Breakdown with example                 │
└─────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────┐
│ 2. SCORING BREAKDOWN FORMAT                         │
│    - Main Zones: point totals + top contributors    │
│    - Zone 3 Sub-zones: A/B/C breakdown              │
│    - Winner Margin calculation                      │
│    - Example output for reference                   │
└─────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────┐
│ 3. PRECEDENCE RULES (3-STEP DECISION TREE)          │
│                                                      │
│    STEP 1: Check GATING conditions                  │
│    ├─ Z5 Q1 (Legal) = Yes → FORCE Zone 5           │
│    └─ Z4 High-risk → FORCE Zone 4                   │
│                                                      │
│    STEP 2: Use SCORING (accumulative)               │
│    ├─ Tally points for each zone                    │
│    ├─ Questions can add to MULTIPLE zones           │
│    └─ Highest total wins                            │
│                                                      │
│    STEP 3: Determine SUB-ZONE (Zone 3 only)        │
│    ├─ Zone 3A: Lockup indicators                    │
│    ├─ Zone 3B: Sub-brand indicators                 │
│    └─ Zone 3C: Integrated product indicators        │
└─────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────┐
│ 4. QUICK SCORING REFERENCE                          │
│    - Zone 4: Key questions & point values           │
│    - Zone 5: Gating vs. point questions             │
│    - Zone 1: Integration indicators                 │
│    - Zone 3: Endorsement & subzone drivers          │
└─────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────┐
│ 5. CONFIDENCE CALCULATION                           │
│    Evidence (0-40) + Completeness (0-30)            │
│    + Conflict Resolution (0-30) = N/100             │
└─────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────┐
│ 6. FORMATTING RULES                                 │
│    - Anchors for deep linking                       │
│    - Section length limits (≤120 words)             │
│    - Citation format: (Q#) or (Not provided)        │
└─────────────────────────────────────────────────────┘
```

---

## Decision Tree Logic

### The 3-Step Process Explained

#### STEP 1: Gating Conditions (Override Everything)

```
┌─────────────────────────────────────┐
│ Is there a legal restriction        │
│ preventing Hexagon branding?        │
│ (Z5 Q1)                             │
└───────────┬─────────────────────────┘
            │
    ┌───────┴───────┐
    │ YES           │ NO
    ↓               ↓
┌─────────┐    Continue to
│ ZONE 5  │    Z4 check
│ (GATE)  │         │
└─────────┘         ↓
            ┌───────────────────────┐
            │ Do high-risk Z4       │
            │ criteria apply?       │
            │ (Contracts, trust,    │
            │ stakeholder objection)│
            └───────┬───────────────┘
                    │
            ┌───────┴───────┐
            │ YES           │ NO
            ↓               ↓
        ┌─────────┐    Continue to
        │ ZONE 4  │    STEP 2
        │ (GATE)  │    (Scoring)
        └─────────┘
```

**Why gates first:**
- Some brands legally CAN'T have Hexagon branding (Zone 5)
- Some brands MUST stay independent for business reasons (Zone 4)
- These override all other considerations

#### STEP 2: Accumulative Scoring

```
For each question in assessment:
  ├─ Add points to applicable zones
  │  Example: Z5 Q2 (No integration plan)
  │  └─ Answer = No → +3 points to Z5
  │  └─ Answer = Yes → +1 point to Z1 AND +1 point to Z3
  │
  └─ Continue through all questions

Final tallies:
├─ Zone 1: 8 points
├─ Zone 3: 22 points ← WINNER
├─ Zone 4: 6 points
└─ Zone 5: 3 points
```

**Key insight:** Questions aren't mutually exclusive. A single answer can add points to multiple zones simultaneously.

**Example from rules:**
```
Z1 Q1 (Revenue contribution):
- <20% → +3 Z1
- 20-70% → +2 Z3A
- >70% → +9 Z2B (Leica only)
```

One question, multiple possible zone impacts.

#### STEP 3: Sub-Zone Determination (Zone 3 Only)

```
If Zone 3 wins:

  Calculate 3A score:
  ├─ Removal causes attrition? (+2)
  ├─ Complex transition >12mo? (+1)
  ├─ Revenue 20-70%? (+2)
  ├─ Outperforms Hexagon metrics? (+2)
  ├─ Strong awareness ≥40% for 3+ years? (+2)
  └─ Generates demand independently? (+3)

  Calculate 3B score:
  ├─ Part of Hexagon platform? (+2)
  ├─ Easier transition <12mo? (+2)
  ├─ Moderate equity signals
  └─ Product/experience loyalty

  Calculate 3C score:
  ├─ Embedded in tech stacks
  ├─ No independent marketing? (+2)
  └─ Primarily product name

  Highest sub-zone score → Final designation
```

**Result formats:**
- Zone 3A → Lockup (brand keeps full logo with Hexagon)
- Zone 3B → Sub-brand (name-only, simplified identity)
- Zone 3C → Integrated product (embedded, low-risk)

---

## Scoring Reference Table Rationale

### Why Include This?

The rules file is 1781 lines long. While comprehensive, it's too large for the AI to efficiently recall specific point values in real-time. The Quick Scoring Reference acts as an index to the most important patterns.

### What's Included vs. Excluded

**Included (25 key questions):**
- **Gating conditions** (must get these right)
- **High-point-value questions** (biggest impact on results)
- **Ambiguous questions** (questions that add to multiple zones)
- **Sub-zone determinants** (Zone 3A/3B/3C drivers)

**Excluded:**
- Binary questions with obvious scoring
- Rare edge cases
- Clarification questions that don't affect points

### Example: Why Z5 Q2 Is Included

```
ZONE 5:
- Q2 (No integration plan): No = +3 Z5 | Yes = +1 Z1, +1 Z3
```

**Rationale:**
1. **High impact:** ±3 points is significant
2. **Multi-zone:** Affects Z1, Z3, and Z5 simultaneously
3. **Counterintuitive:** "Yes" adds to TWO zones, not just one
4. **Common:** Most brands have this question answered

This is exactly the type of question the AI needs quick access to.

### Example: Z4 Q10 Edge Case

```
ZONE 4:
- Q10 (Top 2, endorsement weakens): Yes = +2 Z4 | No = +2 Z3A
```

**Rationale:**
1. **Conditional logic:** Only applies if top 2 ranked AND endorsement weakens
2. **Zone 3A bonus:** "No" answer actually helps Zone 3A
3. **Critical distinction:** Separates Z4 (must be independent) from Z3A (can be endorsed)

Without this reference, AI might miss that a "No" here is actually a +2 Z3A signal.

---

## Post-Processing Validation

### Validation Rules

#### 1. Zone 5 Gating Violations (ERROR)
```python
if zone5_data.get("active_restriction_preventing_hex"):
    if zone != "5":
        logger.error(f"❌ Z5 Q1 gating condition present but assigned Zone {zone}")
```

**Why:** This is a hard rule. Legal restrictions MUST force Zone 5.

#### 2. Zone 4 Trigger Warnings (WARNING)
```python
z4_triggers = [
    ("hex_branding_reduces_trust", "Q2: Hex branding reduces trust"),
    ("hex_link_creates_risk", "Q3: Hex link creates risk"),
    ("stakeholders_object_elimination", "Q8: Stakeholders object"),
    ("rebrand_invalidates_contracts", "Q9: Contracts invalidated")
]

if z4_trigger_count > 0 and zone != "4":
    logger.warning(f"⚠️ {z4_trigger_count} Zone 4 triggers but assigned Zone {zone}")
```

**Why:** Z4 triggers strongly suggest independence needed, but could be overridden by higher Z3 score. Worth flagging.

#### 3. Zone 3 Sub-Zone Logic (WARNING)
```python
if subzone == "A" and z3a_score < 2:
    logger.warning(f"⚠️ Zone 3A assigned but only {z3a_score} strong indicators")
elif subzone == "B" and z3a_score >= 3:
    logger.warning(f"⚠️ Zone 3B assigned but {z3a_score} Z3A indicators (may warrant 3A)")
```

**Why:** Helps catch borderline cases where sub-zone might be misclassified.

#### 4. Zone 1 Revenue Check (WARNING)
```python
if zone == "1" and zone1_data.get("pct_of_division_revenue") in ["20-70", "> 70"]:
    logger.warning(f"⚠️ Zone 1 with revenue {pct}, usually Z3A or Z2B")
```

**Why:** High revenue brands are rarely integrated into masterbrand. This catches potential errors.

### Validation Output Example

**Correct assignment:**
```
✅ [NovAtel] Validation complete: Zone 3A
```

**Borderline case:**
```
⚠️ [TechBrand] Zone 3B assigned but 3 Z3A indicators present (may warrant 3A)
```

**Critical error:**
```
❌ [LegalBrand] Z5 Q1 gating condition (legal restriction) present but assigned Zone 3
```

---

## Benefits of This Architecture

### 1. Separation of Concerns
- **System prompt:** Authority and rules
- **Developer prompt:** Technical logic and format
- **User prompt:** Data only

**Why it matters:** Changes to scoring logic don't require reloading the entire rules file.

### 2. Transparency
- AI must show scoring breakdown
- Users can audit the math
- Easier to identify errors

**Before:** "Zone 3" (no explanation)
**After:** "Zone 3: 22 points (Q8a removal risk +2, Q8b complex transition +1, ...)"

### 3. Validation Safety Net
- Catches obvious errors automatically
- No user-facing impact (only logs)
- Provides debugging breadcrumbs

**Example:** User reports incorrect zone → Check Railway logs → See validation warning → Know where to investigate

### 4. Maintainability
- Quick Reference makes common patterns explicit
- Less reliance on AI "remembering" rules
- Self-documenting prompt structure

**Before:** Hope AI recalls correct scoring from 1781-line file
**After:** AI has indexed lookup table for key questions

### 5. Consistency
- Same scoring logic every time
- Temperature = 0.1 (deterministic)
- Validation ensures logic is followed

**Result:** Same assessment should produce same zone recommendation every time.

---

## Configuration

### Key Settings

```python
# OpenAI Configuration
self.config.openai_model = "gpt-4o"  # Latest model
self.config.temperature = 0.1  # Low for consistency
self.config.openai_timeout = 30.0  # Seconds
self.config.openai_max_retries = 3  # Exponential backoff

# Prompt Components
self.system_prompt = f"""..."""  # Rules file (1781 lines)
self.developer_prompt = """..."""  # Scoring logic (180 lines)
user_msg = f"""..."""  # Assessment JSON (varies)
```

### Why These Settings?

**Temperature 0.1:**
- Near-deterministic outputs
- Same assessment → Same result
- Reduces creative interpretation
- Still allows minor variation for readability

**GPT-4o:**
- Best reasoning capabilities
- Handles complex scoring logic
- Understands structured JSON + markdown
- Can cite specific questions (Q#)

**3 Retries with Backoff:**
- Handles transient API errors
- Exponential delays (2^n seconds)
- Most requests succeed on first try

---

## Future Improvement Ideas

### 1. Confidence Calibration
Currently confidence is AI-estimated. Could validate:
```python
if confidence > 90 and winner_margin < 5:
    logger.warning("High confidence but close margin")
```

### 2. Score Verification
Parse scoring breakdown and verify math:
```python
def verify_scoring_math(breakdown_text):
    """Extract point values and verify they sum correctly"""
    # Would catch arithmetic errors
```

### 3. Historical Tracking
Store all assessments + scores:
```python
{
  "brand": "NovAtel",
  "timestamp": "2025-10-27",
  "zone": "3A",
  "scores": {"Z1": 8, "Z3": 22, "Z4": 6, "Z5": 3},
  "confidence": 92
}
```

Could analyze:
- Score distributions
- Common misclassifications
- Confidence vs. accuracy

### 4. A/B Testing
Run two scoring strategies in parallel:
- Current (explicit scoring reference)
- Alternative (let AI derive from rules file)

Compare consistency and accuracy.

### 5. User Feedback Loop
Allow users to mark classifications as correct/incorrect:
```
👍 Correct  👎 Incorrect  💬 Needs Discussion
```

Build training data for fine-tuning or prompt improvements.

---

## Summary

The Brand Zoning API uses a three-prompt architecture with explicit scoring logic, transparency requirements, and post-processing validation to ensure reliable and auditable zone recommendations.

**Key innovations:**
1. **Gating → Scoring → Sub-zone** decision tree
2. **Scoring breakdown** in every output
3. **Quick reference table** for AI
4. **Post-processing validation** with logged warnings

**Result:** Consistent, transparent, debuggable zone classifications that follow the rules file logic while remaining auditable by humans.

---

## Appendix: Complete Developer Prompt

```python
self.developer_prompt = """You MUST output, in order:
1) H1 line: "# Zone X[Subzone] — [Zone Name] (Recommended)"
2) **CONCLUSION:** ...
3) Confidence block with exact two lines + 1–3 bullets
4) **SCORING BREAKDOWN:** Show all zone scores with question tallies
5) Zone-Specific Assessment
6) Strategic Recommendations
7) Risk Analysis & Mitigation
8) Next Steps & Action Items
9) Machine-Readable Summary as fenced ```json

Scoring Breakdown Format:
**SCORING BREAKDOWN**

Main Zones:
- Zone 1: X points (list top 3-5 contributing questions)
- Zone 3: X points ← WINNER (list top 3-5 contributing questions)
- Zone 4: X points (list top 3-5 contributing questions)
- Zone 5: X points (list top 3-5 contributing questions)

Zone 3 Sub-zones:
- 3A (Lockup): X points ← WINNER (list top 3 indicators)
- 3B (Sub-brand): X points (list top 3 indicators)
- 3C (Integrated): X points (list top 3 indicators)

Winner Margin: X points ahead of second place

Precedence Rules (CRITICAL - Follow Exactly):

STEP 1 - Check GATING conditions (immediate assignment):
- Z5 Q1: Legal/compliance restriction = Yes → FORCE Zone 5 (stop)
- Z4: High-risk independence criteria met → FORCE Zone 4

STEP 2 - If no gates triggered, use SCORING (accumulative):
- Each question contributes points to one or more zones (Z1, Z3, Z4, Z5)
- Questions can add points to MULTIPLE zones simultaneously
- Tally ALL points across ALL questions for each zone
- Highest total zone score wins

STEP 3 - Determine SUB-ZONE (for Zone 3 only):
If Zone 3 wins, determine A/B/C based on indicators...

Quick Scoring Reference (Key Questions):
[Full reference table as shown above]

Confidence = [Evidence 0–40] + [Completeness 0–30] + [Conflict 0–30] = N/100.
If thin data, produce a Provisional score.

Formatting:
- Anchors: zone-recommendation, conclusion, confidence, etc.
- ≤120 words per section; bullets OK; no extra sections.
- Cite evidence with (Q#) or (Not provided in assessment)."""
```

This prompt is approximately **280 lines** and provides comprehensive guidance while remaining under token limits for GPT-4o context windows.
