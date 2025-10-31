# Brand Zoning API Documentation

**Version:** 1.0.0
**Base URL:** `https://web-production-13c5e.up.railway.app`
**Last Updated:** October 31, 2025

## Table of Contents
- [Overview](#overview)
- [Authentication](#authentication)
- [Rate Limiting](#rate-limiting)
- [Endpoints](#endpoints)
- [Error Handling](#error-handling)
- [Examples](#examples)
- [Changelog](#changelog)

---

## Overview

The Brand Zoning API analyzes brand architecture assessments and provides AI-powered zone recommendations using OpenAI's GPT-4. The API processes assessment data and returns both a comprehensive markdown report and machine-readable JSON summary.

### Key Features
- API key authentication for secure access
- Rate limiting to prevent abuse
- Comprehensive error handling with retry logic
- Health check endpoint for monitoring
- CORS support for web applications

---

## Authentication

### API Key Authentication

All protected endpoints require authentication via the `X-API-Key` header.

**Header Format:**
```
X-API-Key: hbz_your_api_key_here
```

**Key Characteristics:**
- Prefix: `hbz_` (Hexagon Brand Zoner)
- Case-sensitive
- Must match exactly (hard fail on mismatch)

**Error Responses:**
- `401 Unauthorized` - Missing API key
- `401 Unauthorized` - Invalid API key

**Example:**
```bash
curl -X POST https://web-production-13c5e.up.railway.app/zone \
  -H "Content-Type: application/json" \
  -H "X-API-Key: hbz_your_api_key_here" \
  -d @assessment.json
```

### Public Endpoints
The following endpoints do NOT require authentication:
- `GET /` - API information
- `GET /health` - Health check

---

## Rate Limiting

Rate limits are enforced per IP address to prevent abuse.

| Endpoint | Limit | Window |
|----------|-------|--------|
| `POST /zone` | 50 requests | 1 hour |
| `GET /debug/prompts` | 10 requests | 1 hour |

**Rate Limit Exceeded:**
- **Status Code:** `429 Too Many Requests`
- **Response:** `{"detail": "Rate limit exceeded"}`
- **Behavior:** Rate limits reset on service restart (in-memory tracking)

---

## Endpoints

### 1. Root Endpoint

**`GET /`**

Returns API information and available endpoints.

**Authentication:** None required

**Response:**
```json
{
  "name": "Brand Zoning API",
  "version": "1.0.0",
  "description": "AI-powered brand architecture zone recommendations",
  "endpoints": {
    "POST /zone": "Generate zone recommendation from assessment",
    "GET /health": "Health check endpoint"
  }
}
```

---

### 2. Health Check

**`GET /health`**

Monitors service health and configuration status.

**Authentication:** None required

**Response:**
```json
{
  "status": "healthy",
  "openai": "configured",
  "rules_loaded": true,
  "model": "gpt-4o"
}
```

**Response Fields:**
- `status` - Service health status (`healthy` or `unhealthy`)
- `openai` - OpenAI API key status (`configured` or `missing`)
- `rules_loaded` - Whether business rules file is loaded
- `model` - OpenAI model being used

---

### 3. Zone Recommendation

**`POST /zone`**

Generates a brand zone recommendation from assessment data.

**Authentication:** Required (`X-API-Key` header)
**Rate Limit:** 50 requests per hour per IP

**Request Headers:**
```
Content-Type: application/json
X-API-Key: hbz_your_api_key_here
```

**Request Body:**
Any JSON object containing brand assessment data. Common fields:
```json
{
  "brand": "Brand Name",
  "question_1": "Answer to question 1",
  "question_2": "Answer to question 2",
  ...
}
```

See `samples/novatel_assessment.json` for a complete example.

**Success Response (200 OK):**
```json
{
  "report_markdown": "# Zone 3A — Endorsed Brand Architecture (Recommended)\n\n**CONCLUSION:** ...",
  "summary": {
    "brand": "Brand Name",
    "zone": "3",
    "subzone": "3A",
    "zone_name": "Endorsed Brand Architecture",
    "confidence": 82,
    "evidence": 32,
    "completeness": 25,
    "conflict_resolution": 25,
    "drivers": ["Key driver 1", "Key driver 2"],
    "conflicts": ["Conflict 1"],
    "risks": ["Risk 1", "Risk 2"],
    "next_steps": ["Action 1", "Action 2"]
  }
}
```

**Response Fields:**

`report_markdown` (string):
- Full markdown report with zone recommendation
- Includes conclusion, confidence scoring, assessment breakdown
- Strategic recommendations and risk analysis
- Formatted for rendering or export

`summary` (object):
- `brand` - Brand name from assessment
- `zone` - Recommended zone (1, 3, 4, or 5)
- `subzone` - Sub-zone classification (e.g., "3A", "3B")
- `zone_name` - Human-readable zone name
- `confidence` - Overall confidence score (0-100)
- `evidence` - Evidence strength score (0-40)
- `completeness` - Data completeness score (0-30)
- `conflict_resolution` - Conflict resolution score (0-30)
- `drivers` - Array of key decision drivers
- `conflicts` - Array of identified conflicts
- `risks` - Array of identified risks
- `next_steps` - Array of recommended actions

**Error Responses:**

| Status | Condition | Response |
|--------|-----------|----------|
| `401` | Missing API key | `{"detail": "Missing API key. Include X-API-Key header."}` |
| `401` | Invalid API key | `{"detail": "Invalid API key"}` |
| `422` | Invalid request body | `{"detail": "Validation error"}` |
| `429` | Rate limit exceeded | `{"detail": "Rate limit exceeded"}` |
| `503` | OpenAI service unavailable | `{"detail": "OpenAI service unavailable: [error details]"}` |
| `500` | Internal server error | `{"detail": "Internal server error"}` |

**Typical Response Time:** 10-20 seconds (includes OpenAI API call)

---

### 4. Debug Prompts

**`GET /debug/prompts`**

Returns the prompts being sent to OpenAI for debugging and transparency.

**Authentication:** Required (`X-API-Key` header)
**Rate Limit:** 10 requests per hour per IP

**⚠️ Warning:** This endpoint exposes your prompt engineering. Use with caution and only in trusted environments.

**Request Headers:**
```
X-API-Key: hbz_your_api_key_here
```

**Response (200 OK):**
```json
{
  "system_prompt": "Full system prompt text...",
  "system_prompt_length": 1234,
  "developer_prompt": "Full developer prompt text...",
  "developer_prompt_length": 5678,
  "rules_file_loaded": true,
  "rules_file_length": 9012,
  "rules_preview": "First 500 characters of rules...",
  "model": "gpt-4o",
  "temperature": 0.3
}
```

---

## Error Handling

### Error Response Format

All errors follow this structure:
```json
{
  "detail": "Human-readable error message"
}
```

### HTTP Status Codes

| Code | Meaning | Description |
|------|---------|-------------|
| `200` | OK | Request successful |
| `401` | Unauthorized | Missing or invalid API key |
| `422` | Unprocessable Entity | Invalid request format |
| `429` | Too Many Requests | Rate limit exceeded |
| `500` | Internal Server Error | Unexpected server error |
| `503` | Service Unavailable | OpenAI service temporarily unavailable |

### Retry Logic

The API implements automatic retry logic for OpenAI service failures:
- **Retries:** Up to 3 attempts
- **Backoff:** Exponential (1s, 2s, 4s)
- **Transient Errors:** Automatically retried
- **Permanent Errors:** Returned immediately

**Best Practices for Clients:**
1. Implement exponential backoff for `503` errors
2. Do not retry `401` or `422` errors
3. Monitor for `429` errors and adjust request frequency
4. Set reasonable timeout values (30+ seconds recommended)

---

## Examples

### Example 1: Basic Zone Recommendation

```bash
curl -X POST https://web-production-13c5e.up.railway.app/zone \
  -H "Content-Type: application/json" \
  -H "X-API-Key: hbz_tkTathhvlNfzZJsAPjqAkZz1ByUTEbRkofEduW3Mkqk" \
  -d '{
    "brand": "NovAtel",
    "question_1": "Yes",
    "question_2": "No"
  }'
```

### Example 2: Using Sample Assessment File

```bash
curl -X POST https://web-production-13c5e.up.railway.app/zone \
  -H "Content-Type: application/json" \
  -H "X-API-Key: hbz_tkTathhvlNfzZJsAPjqAkZz1ByUTEbRkofEduW3Mkqk" \
  -d @samples/novatel_assessment.json
```

### Example 3: Health Check

```bash
curl https://web-production-13c5e.up.railway.app/health
```

### Example 4: Error Handling (Invalid API Key)

```bash
curl -X POST https://web-production-13c5e.up.railway.app/zone \
  -H "Content-Type: application/json" \
  -H "X-API-Key: wrong-key" \
  -d '{"brand": "Test"}' \
  -w "\nHTTP Status: %{http_code}\n"
```

**Response:**
```json
{"detail":"Invalid API key"}
HTTP Status: 401
```

### Example 5: JavaScript/TypeScript Integration

```typescript
const response = await fetch('https://web-production-13c5e.up.railway.app/zone', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'X-API-Key': process.env.RAILWAY_API_KEY || ''
  },
  body: JSON.stringify({
    brand: 'NovAtel',
    question_1: 'Yes',
    question_2: 'No'
  })
});

if (!response.ok) {
  if (response.status === 401) {
    throw new Error('Invalid API key');
  } else if (response.status === 429) {
    throw new Error('Rate limit exceeded');
  } else if (response.status === 503) {
    throw new Error('Service temporarily unavailable');
  }
  throw new Error(`API error: ${response.status}`);
}

const data = await response.json();
console.log('Zone:', data.summary.zone);
console.log('Confidence:', data.summary.confidence);
```

---

## Security Best Practices

### API Key Management
1. **Never commit API keys** to version control
2. **Store in environment variables** (Railway, Replit Secrets, etc.)
3. **Rotate keys periodically** (update both server and clients)
4. **Use different keys** for development and production
5. **Monitor for unauthorized usage** in Railway logs

### CORS Configuration
- Default: Allows all origins (`*`)
- Production: Set `CORS_ORIGINS` environment variable to specific domains
- Example: `CORS_ORIGINS=https://your-app.repl.co,https://your-domain.com`

### Rate Limit Monitoring
- Monitor Railway logs for `429` responses
- Adjust request patterns to stay within limits
- Consider requesting limit increases for production use

### Logging
- Authentication failures are logged with truncated API key
- All requests logged with brand name and zone result
- Use `LOG_LEVEL=DEBUG` for detailed troubleshooting

---

## Changelog

### Version 1.0.0 (October 31, 2025)

**Added:**
- API key authentication via `X-API-Key` header
- Rate limiting: 50 req/hour for `/zone`, 10 req/hour for `/debug/prompts`
- `/debug/prompts` endpoint for transparency
- Comprehensive error handling
- Health check endpoint
- Zone overview definitions in reports
- Numeric confidence scoring (0-100)
- Sub-zone determination (3A, 3B, 3C)

**Security:**
- Hard fail on missing/invalid API keys (401)
- Per-IP rate limiting with 429 responses
- Structured logging for security monitoring
- CORS configuration support

**Documentation:**
- Complete API documentation
- Security best practices
- Code examples for multiple languages
- Error handling guidelines

---

## Support

**Issues:** https://github.com/FirstPersonSF/hex-brand-zoner/issues
**Documentation:** https://github.com/FirstPersonSF/hex-brand-zoner/blob/master/README.md
**Railway Deployment:** https://web-production-13c5e.up.railway.app

For questions or support, please open an issue on GitHub.
