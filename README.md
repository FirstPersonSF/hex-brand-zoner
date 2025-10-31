# Brand Zoning API — Production Ready (Railway‑ready)

A production-grade FastAPI service that turns your Brand Architecture Assessment into a zone recommendation + exec‑ready report, using OpenAI Responses API.

## Features
- ✅ Comprehensive error handling with retry logic
- ✅ Structured logging for production debugging
- ✅ Health check endpoint for monitoring
- ✅ Modular architecture (config, services, utils)
- ✅ 80%+ test coverage with pytest
- ✅ Precedence & tie‑breaker rules baked into the prompt
- ✅ Exact section order + anchors for UI deep‑linking
- ✅ Returns full markdown report **and** machine‑readable JSON
- ✅ Railway‑ready with health checks
- ✅ API key authentication for secure access
- ✅ Rate limiting (50 requests/hour per IP)

---

## Quick Start (Local)

```bash
python -m venv .venv && source .venv/bin/activate  # on Windows: .venv\Scripts\activate
pip install -r requirements.txt
export OPENAI_API_KEY=sk-...
export API_KEY=hbz_your_api_key_here  # Generate with: python3 -c "import secrets; print(f'hbz_{secrets.token_urlsafe(32)}')"
export OPENAI_MODEL=gpt-4o
export SYSTEM_RULES_PATH="$(pwd)/rules/HEX 5112 - Brand Architecture - Full Set of Questions & Logic Scoring v009.md"
uvicorn app:app --reload --port 8080
```

Test endpoints:
```bash
# Health check (no authentication required)
curl http://localhost:8080/health

# Zone recommendation (requires API key)
curl -X POST http://localhost:8080/zone \
  -H "Content-Type: application/json" \
  -H "X-API-Key: hbz_your_api_key_here" \
  -d @samples/novatel_assessment.json

# API info (no authentication required)
curl http://localhost:8080/
```

---

## Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=. --cov-report=term-missing

# Run only unit tests
pytest -m unit

# Run only integration tests
pytest -m integration
```

---

## Deploy to Railway

1. Push this folder to GitHub.
2. In Railway: **New Project → Deploy from GitHub** → select your repo.
3. Set Variables:
   - `OPENAI_API_KEY` = `sk-...`
   - `API_KEY` = `hbz_...` (generate with: `python3 -c "import secrets; print(f'hbz_{secrets.token_urlsafe(32)}')"`)
   - `OPENAI_MODEL` = `gpt-4o` (optional, defaults to gpt-4o)
   - `SYSTEM_RULES_PATH` = `/app/rules/HEX 5112 - Brand Architecture - Full Set of Questions & Logic Scoring v009.md`
   - `LOG_LEVEL` = `INFO` (optional)
   - `CORS_ORIGINS` = `https://your-replit-app.repl.co` (optional, defaults to *)
4. Deploy. Railway uses `Railway.toml` to start:
   `uvicorn app:app --host 0.0.0.0 --port ${PORT}`
5. Railway will monitor `/health` endpoint for service status
6. **Important:** Add the `X-API-Key` header to all `/zone` requests from your client (Replit)

Endpoints:
```
GET  https://<your-service>.up.railway.app/          (no auth)
GET  https://<your-service>.up.railway.app/health    (no auth)
POST https://<your-service>.up.railway.app/zone      (requires X-API-Key header)
GET  https://<your-service>.up.railway.app/debug/prompts  (requires X-API-Key header, rate limited)
```

---

## API Endpoints

### `GET /`
Returns API information and available endpoints.

**Response:**
```json
{
  "name": "Brand Zoning API",
  "version": "1.0.0",
  "description": "AI-powered brand architecture zone recommendations",
  "endpoints": { ... }
}
```

### `GET /health`
Health check endpoint for monitoring.

**Response:**
```json
{
  "status": "healthy",
  "openai": "configured",
  "rules_loaded": true,
  "model": "gpt-4o"
}
```

### `POST /zone`
Generate zone recommendation from assessment.

**Authentication:** Required (X-API-Key header)
**Rate Limit:** 50 requests per hour per IP address

**Request Headers:**
- `X-API-Key: hbz_your_api_key_here` (required)
- `Content-Type: application/json` (required)

**Request Body:** Full assessment JSON (any structure, see `samples/novatel_assessment.json`)

**Response:**
```json
{
  "report_markdown": "# Zone X — [Name] (Recommended)\n...",
  "summary": {
    "brand": "...",
    "zone": "1",
    "zone_name": "Full Masterbrand Integration",
    "confidence": 85,
    "drivers": [...],
    "conflicts": [...],
    "risks": [...],
    "next_steps": [...]
  }
}
```

**Error Responses:**
- `401` - Missing or invalid API key
- `422` - Invalid request body
- `429` - Rate limit exceeded (50 requests/hour)
- `503` - OpenAI service unavailable (retry recommended)
- `500` - Internal server error

### `GET /debug/prompts`
Debug endpoint to inspect the prompts being sent to OpenAI.

**Authentication:** Required (X-API-Key header)
**Rate Limit:** 10 requests per hour per IP address

**⚠️ Warning:** This endpoint exposes your prompt engineering. Use with caution.

**Request Headers:**
- `X-API-Key: hbz_your_api_key_here` (required)

**Response:**
```json
{
  "system_prompt": "...",
  "system_prompt_length": 1234,
  "developer_prompt": "...",
  "developer_prompt_length": 5678,
  "rules_file_loaded": true,
  "rules_file_length": 9012,
  "rules_preview": "...",
  "model": "gpt-4o",
  "temperature": 0.3
}
```

**Error Responses:**
- `401` - Missing or invalid API key
- `429` - Rate limit exceeded (10 requests/hour)

---

## Project Structure

```
.
├── app.py                 # FastAPI application
├── config.py              # Configuration management
├── services/
│   └── openai_service.py  # OpenAI integration with retry logic
├── utils/
│   └── logging_config.py  # Structured logging
├── tests/
│   ├── test_api.py        # API endpoint tests
│   ├── test_config.py     # Configuration tests
│   ├── test_openai_service.py  # OpenAI service tests
│   ├── test_validation.py # Input validation tests
│   ├── test_parsing.py    # Response parsing tests
│   └── test_integration.py # Integration tests
├── requirements.txt       # Python dependencies
├── pytest.ini             # Test configuration
├── Railway.toml           # Railway deployment config
├── rules/
│   └── HEX 5112 - ...md  # Zoning rules
├── samples/
│   └── novatel_assessment.json  # Sample request
└── docs/
    └── plans/             # Design documents
```

---

## Configuration

All configuration via environment variables:

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `OPENAI_API_KEY` | ✅ Yes | - | OpenAI API key |
| `API_KEY` | ✅ Yes | - | API key for authentication (prefix: `hbz_`) |
| `OPENAI_MODEL` | No | `gpt-4o` | OpenAI model to use |
| `SYSTEM_RULES_PATH` | No | `/app/rules/HEX-5112.md` | Path to rules file |
| `LOG_LEVEL` | No | `INFO` | Logging level (DEBUG, INFO, WARNING, ERROR) |
| `CORS_ORIGINS` | No | `*` | Comma-separated allowed origins |

---

## Development

### Running Locally
```bash
source .venv/bin/activate
uvicorn app:app --reload --port 8080
```

### Running Tests
```bash
pytest -v
```

### Code Coverage
```bash
pytest --cov=. --cov-report=html
open htmlcov/index.html
```

---

## Security

### API Key Authentication
All `/zone` and `/debug/prompts` endpoints require authentication via the `X-API-Key` header. The API key must:
- Start with prefix `hbz_` (Hexagon Brand Zoner)
- Be stored in the `API_KEY` environment variable
- Match exactly for authentication to succeed (hard fail on mismatch)

Generate a secure API key:
```bash
python3 -c "import secrets; print(f'hbz_{secrets.token_urlsafe(32)}')"
```

### Rate Limiting
- `/zone` endpoint: 50 requests per hour per IP address
- `/debug/prompts` endpoint: 10 requests per hour per IP address
- Rate limits are enforced in-memory (reset on service restart)
- Exceeded limits return `429 Too Many Requests`

### Best Practices
- ✅ Keep `OPENAI_API_KEY` and `API_KEY` in environment variables, **never** in code
- ✅ Set `CORS_ORIGINS` to specific domains (e.g., your Replit app) in production
- ✅ Rotate `API_KEY` periodically and after any suspected compromise
- ✅ Monitor `/health` endpoint for service availability
- ✅ Review logs regularly for authentication failures and rate limit violations
- ✅ Store API keys securely (Railway environment variables, not in git)

---

## License
MIT
