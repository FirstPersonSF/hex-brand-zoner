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

---

## Quick Start (Local)

```bash
python -m venv .venv && source .venv/bin/activate  # on Windows: .venv\Scripts\activate
pip install -r requirements.txt
export OPENAI_API_KEY=sk-...
export OPENAI_MODEL=gpt-4o
export SYSTEM_RULES_PATH="$(pwd)/rules/HEX 5112 - Brand Architecture - Full Set of Questions & Logic Scoring v009.md"
uvicorn app:app --reload --port 8080
```

Test endpoints:
```bash
# Health check
curl http://localhost:8080/health

# Zone recommendation
curl -X POST http://localhost:8080/zone \
  -H "Content-Type: application/json" \
  -d @samples/novatel_assessment.json

# API info
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
   - `OPENAI_MODEL` = `gpt-4o` (optional, defaults to gpt-4o)
   - `SYSTEM_RULES_PATH` = `/app/rules/HEX 5112 - Brand Architecture - Full Set of Questions & Logic Scoring v009.md`
   - `LOG_LEVEL` = `INFO` (optional)
   - `CORS_ORIGINS` = `https://your-replit-app.repl.co` (optional, defaults to *)
4. Deploy. Railway uses `Railway.toml` to start:
   `uvicorn app:app --host 0.0.0.0 --port ${PORT}`
5. Railway will monitor `/health` endpoint for service status

Endpoints:
```
GET  https://<your-service>.up.railway.app/
GET  https://<your-service>.up.railway.app/health
POST https://<your-service>.up.railway.app/zone
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
- `422` - Invalid request body
- `503` - OpenAI service unavailable (retry recommended)
- `500` - Internal server error

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

## Security Notes
- Keep `OPENAI_API_KEY` in environment variables, **not** in code
- Set `CORS_ORIGINS` to your Replit app domain in production
- Consider adding API key authentication for production use
- Monitor `/health` endpoint for service availability

---

## License
MIT
