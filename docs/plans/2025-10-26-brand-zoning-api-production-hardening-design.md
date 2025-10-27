# Brand Zoning API - Production Hardening Design

**Date**: 2025-10-26
**Status**: Approved
**Approach**: Comprehensive Testing & Hardening

## Overview

Transform the existing Brand Zoning API prototype into a production-ready service with comprehensive testing, robust error handling, and Railway deployment. The API receives brand architecture assessments from a Replit frontend app and returns AI-generated zone recommendations via OpenAI.

## Architecture

### System Flow
```
Replit App → Railway API → OpenAI Responses API → Railway API → Replit App
```

### Core Components

1. **FastAPI Backend** (`app.py` enhanced)
   - Request validation with Pydantic models
   - Environment variable validation on startup
   - Structured error responses with error codes
   - Request ID generation for tracing

2. **OpenAI Integration** (`services/openai_client.py`)
   - Retry logic with exponential backoff (3 retries max)
   - Timeout handling (30s default)
   - Response validation against schema
   - Markdown extraction and JSON parsing with error recovery

3. **Configuration Management** (`config.py`)
   - Environment variable loading with defaults
   - Rules file validation on startup
   - Model configuration (temperature, timeout)
   - Feature flags for optional behavior

4. **Testing Suite** (`tests/`)
   - Unit tests for validation, parsing, error handling
   - Integration tests with mocked OpenAI
   - Contract tests for API compatibility
   - End-to-end tests with sample data

5. **Logging & Monitoring** (`utils/logging.py`)
   - Structured JSON logging for production
   - Request/response logging (sanitized)
   - Performance metrics tracking
   - Error tracking with stack traces

## API Contract (Preserved for Replit Compatibility)

### Existing Endpoint
**POST /zone**
- Request: Assessment JSON (any structure, see `samples/novatel_assessment.json`)
- Response: `{ "report_markdown": "...", "summary": {...} }`
- **Must remain unchanged** - Replit app already integrated

### New Endpoints
**GET /health**
- Returns: `{ "status": "healthy", "openai": "ok", "rules_loaded": true }`
- Used by Railway for monitoring

**GET /**
- Returns: API documentation and version info
- Helpful for developers

## Data Flow & Error Handling

### Request Processing Pipeline
1. **Input Reception** → Validate JSON structure, check size (<1MB)
2. **Environment Check** → Verify OpenAI key, rules file accessible
3. **Assessment Validation** → Pydantic model validation
4. **OpenAI Call** → Retry on transient failures, timeout protection
5. **Response Processing** → Extract markdown + JSON, validate schema
6. **Output Formatting** → Return structured response

### Error Scenarios

| Error Type | HTTP Code | Response | Action |
|------------|-----------|----------|--------|
| Missing/invalid API key | 500 | Configuration error | Check env vars |
| Rules file not found | 200* | Warning logged | Continue with empty rules |
| Malformed assessment | 422 | Field-specific errors | Fix request |
| OpenAI timeout/failure | 503 | Retry guidance | Wait and retry |
| Invalid response format | 500 | Parsing error details | Report bug |
| Rate limit exceeded | 429 | Retry-after header | Back off |

*Rules file missing is non-fatal - system can operate without it

### Retry Strategy
- **OpenAI API calls**: 3 attempts, exponential backoff (1s, 2s, 4s)
- **File operations**: 2 attempts for transient I/O errors
- **No retry** on validation errors (fail fast)

### Logging Levels
- **INFO**: Successful requests, startup events
- **WARNING**: Rules file missing, degraded mode
- **ERROR**: OpenAI failures, parsing errors
- **DEBUG**: Full request/response (development only)

## Testing Strategy

### Unit Tests (isolated, fast)
- `test_extract_summary()` - markdown JSON parsing with edge cases
- `test_load_rules_text()` - file loading, missing files, encoding
- `test_validation()` - Pydantic model validation, size limits
- Environment config loading with missing/invalid values

### Integration Tests (mocked OpenAI)
- Mock OpenAI responses with `pytest-mock`
- Test full request/response cycle without API costs
- Validate schema enforcement on OpenAI output
- Test retry logic with simulated failures

### Contract Tests (schema validation)
- Verify request format matches Replit app expectations
- Validate response structure (`report_markdown`, `summary`)
- Test MACHINE_JSON_SCHEMA against sample outputs
- Ensure backward compatibility

### End-to-End Tests (optional, real API)
- Run against real OpenAI API with test data
- Verify complete flow with actual rules file
- Performance benchmarking (response time <10s target)
- Cost tracking for production estimation

### Test Data
- Use existing `samples/novatel_assessment.json`
- Add edge cases: minimal data, all zones, conflicting signals
- Invalid inputs: malformed JSON, missing fields, oversized payloads
- Expected outputs for regression testing

### Coverage Target
80%+ for core logic (validation, parsing, error handling)

## Railway Deployment

### Environment Variables
Set in Railway dashboard:
- `OPENAI_API_KEY` - OpenAI API key (required, secret)
- `OPENAI_MODEL` - `gpt-4o` or `gpt-4o-mini` (optional, default: gpt-4o)
- `SYSTEM_RULES_PATH` - `/app/rules/HEX-5112.md` (optional, has default)
- `LOG_LEVEL` - `INFO` for production, `DEBUG` for troubleshooting
- `CORS_ORIGINS` - Comma-separated Replit URLs (optional, defaults to `*`)

### Railway.toml Configuration
- Nixpacks builder (existing)
- Health check endpoint monitoring
- Restart policy: `on_failure` (existing)
- PORT binding (Railway auto-assigns)

### Deployment Process
1. Push code to GitHub repository
2. Connect Railway to GitHub repo
3. Set environment variables in Railway dashboard
4. Deploy - Railway auto-builds and starts
5. Test health endpoint: `GET https://<service>.railway.app/health`
6. Test zone endpoint with sample data
7. Update Replit app with Railway URL

### Health Checks
- Railway monitors `/health` endpoint
- Returns `200 OK` if API key valid, rules file loaded
- Returns `503 Service Unavailable` if misconfigured

### Monitoring & Logs
- Railway provides built-in log viewer
- Structured JSON logs for filtering/searching
- Track request volumes, error rates, response times

## Security Considerations

### Current State (MVP)
- CORS: Allow all origins (`*`)
- Authentication: None
- Input validation: Basic JSON structure

### Future Enhancements (when needed)
- CORS allowlist for Replit domains only
- API key authentication via headers
- Rate limiting per client
- Request size limits (already planned at 1MB)
- Input sanitization for log injection prevention

## File Structure

```
hex-brand-zoner/
├── app.py                 # Enhanced FastAPI app
├── config.py              # New: Environment config
├── services/
│   └── openai_client.py   # New: OpenAI integration
├── utils/
│   └── logging.py         # New: Structured logging
├── tests/
│   ├── test_api.py        # New: API endpoint tests
│   ├── test_openai_integration.py  # New: OpenAI mocking
│   ├── test_validation.py # New: Input validation tests
│   ├── test_parsing.py    # New: Response parsing tests
│   └── fixtures/          # New: Test data
├── requirements.txt       # Updated with test deps
├── Railway.toml           # Updated with health check
├── rules/
│   └── HEX-5112.md       # Existing rules file
├── samples/
│   └── novatel_assessment.json  # Existing sample
└── docs/
    └── plans/
        └── 2025-10-26-brand-zoning-api-production-hardening-design.md  # This file
```

## Success Criteria

- [ ] All tests passing with 80%+ coverage
- [ ] Health check endpoint operational
- [ ] Successful deployment to Railway
- [ ] API accessible from Replit app
- [ ] Response time <10s for typical assessments
- [ ] Error handling covers all failure modes
- [ ] Logs provide actionable debugging information
- [ ] Backward compatible with existing Replit integration

## Dependencies

### Production
- `fastapi` - Web framework
- `uvicorn[standard]` - ASGI server
- `openai>=1.40.0` - OpenAI SDK
- `pydantic` - Data validation
- `python-json-logger` - Structured logging

### Development/Testing
- `pytest` - Test framework
- `pytest-mock` - Mocking utilities
- `pytest-cov` - Coverage reporting
- `httpx` - Async HTTP client for testing
- `responses` - HTTP request mocking

## Timeline Estimate

- **Setup & Configuration**: 30 min
- **Code Refactoring**: 1 hour
- **Test Suite Development**: 1.5 hours
- **Local Testing & Debugging**: 45 min
- **Railway Deployment**: 30 min
- **Integration Testing with Replit**: 15 min

**Total**: ~4 hours for comprehensive implementation

## Next Steps

1. Set up git worktree for isolated development
2. Create detailed implementation plan
3. Implement changes following test-driven development
4. Deploy to Railway
5. Validate integration with Replit app
