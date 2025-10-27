# Brand Zoning API — Starter Kit (Railway‑ready)

A minimal FastAPI service that turns your Brand Architecture Assessment into a zone recommendation + exec‑ready report, using OpenAI Responses API.

## Features
- Precedence & tie‑breaker rules baked into the prompt
- Exact section order + anchors for UI deep‑linking
- Returns a full markdown report **and** a machine‑readable JSON block
- Railway‑ready (`Railway.toml`) and local run instructions

---

## Quick Start (Local)

```bash
python -m venv .venv && source .venv/bin/activate  # on Windows: .venv\Scripts\activate
pip install -r requirements.txt
export OPENAI_API_KEY=sk-...
export OPENAI_MODEL=gpt-4o
export SYSTEM_RULES_PATH="$(pwd)/rules/HEX-5112.md"
uvicorn app:app --reload --port 8080
```

Test:
```bash
curl -X POST http://localhost:8080/zone   -H "Content-Type: application/json"   -d @samples/novatel_assessment.json
```

---

## Deploy to Railway

1. Push this folder to GitHub.
2. In Railway: **New Project → Deploy from GitHub** → select your repo.
3. Set Variables:
   - `OPENAI_API_KEY` = `sk-...`
   - `OPENAI_MODEL` = `gpt-4o`
   - `SYSTEM_RULES_PATH` = `/app/rules/HEX-5112.md`
4. Deploy. Railway uses `Railway.toml` to start:  
   `uvicorn app:app --host 0.0.0.0 --port ${PORT}`

Endpoint:
```
POST https://<your-service>.up.railway.app/zone
```

---

## Endpoint

### `POST /zone`
Body: your full assessment JSON (any keys; see `samples/novatel_assessment.json` for structure).  
Response: `{ "report_markdown": "…full report…", "summary": { ... } }`

**Tip:** The API returns both the report and a parsed machine summary (JSON) extracted from the fenced block.

---

## Files

- `app.py` — FastAPI app with OpenAI Responses call and Structured Output schema
- `requirements.txt` — deps
- `Railway.toml` — Railway build & run settings
- `Procfile` — optional alternate start command
- `rules/HEX-5112.md` — put your rules text here
- `samples/novatel_assessment.json` — sample request payload
- `README.md` — you are here

---

## Security Notes
- Keep `OPENAI_API_KEY` in environment variables, **not** in code.
- Consider locking CORS to your UI origin in production (see comment in `app.py`).

---

## License
MIT
