
import os, json, re
from typing import Any, Dict
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from openai import OpenAI

OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
SYSTEM_RULES_PATH = os.getenv("SYSTEM_RULES_PATH", "/app/rules/HEX-5112.md")

client = OpenAI(api_key=OPENAI_API_KEY)
app = FastAPI(title="Brand Zoning API")

# --- CORS (tighten allow_origins in prod) ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class Assessment(BaseModel):
    __root__: Dict[str, Any]

MACHINE_JSON_SCHEMA = {
  "type":"object",
  "additionalProperties": False,
  "properties":{
    "brand":{"type":"string"},
    "zone":{"type":"string","enum":["1","3","4","5"]},
    "zone_name":{"type":"string","enum":[
      "Full Masterbrand Integration","Endorsed Brand",
      "High-Stakes Independence","Legal/Accounting/Integration Hold"
    ]},
    "subzone":{"type":"string"},
    "confidence":{"type":"integer","minimum":0,"maximum":100},
    "drivers":{"type":"array","items":{"type":"string"}},
    "conflicts":{"type":"array","items":{"type":"string"}},
    "risks":{"type":"array","items":{"type":"string"}},
    "next_steps":{"type":"array","items":{"type":"string"}}
  },
  "required":["brand","zone","zone_name","subzone","confidence","drivers","conflicts","risks","next_steps"]
}

def load_rules_text() -> str:
    try:
        with open(SYSTEM_RULES_PATH, "r", encoding="utf-8") as f:
            return f.read()
    except Exception:
        return ""

SYSTEM_PROMPT = f"""You are a strict brand-architecture adjudicator.
Apply these rules verbatim. If the rules file is present, it overrides ambiguities.

=== RULES FILE (if provided) ===
{load_rules_text()}
=== END RULES FILE ===
"""

DEVELOPER_PROMPT = """You MUST output, in order:
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

def extract_summary(markdown: str) -> Dict[str, Any]:
    m = re.search(r"```json\s*(\{.*?\})\s*```", markdown, re.S)
    return json.loads(m.group(1)) if m else {}

@app.post("/zone")
def zone(assessment: Assessment):
    if not OPENAI_API_KEY:
        raise HTTPException(status_code=500, detail="Missing OPENAI_API_KEY")

    user_payload = assessment.__root__

    user_msg = (
        "ASSESSMENT JSON:\n" +
        json.dumps(user_payload, ensure_ascii=False, indent=2) +
        "\n\nFollow all formatting + precedence rules exactly."
    )

    resp = client.responses.create(
        model=OPENAI_MODEL,
        input=[
            {"role":"system","content":SYSTEM_PROMPT},
            {"role":"developer","content":DEVELOPER_PROMPT},
            {"role":"user","content":user_msg},
        ],
        text={
          "format":{
            "type":"json_schema",
            "schema":MACHINE_JSON_SCHEMA
          },
          "require_json": False
        },
        temperature=0.1
    )

    content = resp.output_text
    summary = extract_summary(content)
    return {"report_markdown": content, "summary": summary}
