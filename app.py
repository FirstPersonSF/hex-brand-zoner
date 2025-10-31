import os
from typing import Any, Dict
from fastapi import FastAPI, HTTPException, Header, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import RootModel
from contextlib import asynccontextmanager
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from config import Config, ConfigError
from services.openai_service import OpenAIService, OpenAIServiceError
from utils.logging_config import setup_logging, get_logger

# Initialize configuration and logging
try:
    config = Config()
    setup_logging(config.log_level)
    logger = get_logger(__name__)
except ConfigError as e:
    print(f"Configuration error: {e}")
    raise

# Initialize OpenAI service
openai_service = OpenAIService(config)

# Initialize rate limiter
limiter = Limiter(key_func=get_remote_address)

# API Key verification dependency
def verify_api_key(x_api_key: str = Header(None, alias="X-API-Key")):
    """Verify API key from request header

    Args:
        x_api_key: API key from X-API-Key header

    Returns:
        The API key if valid

    Raises:
        HTTPException: 401 if API key is invalid or missing
    """
    expected_key = os.getenv("API_KEY")

    if not expected_key:
        logger.error("API_KEY environment variable not configured")
        raise HTTPException(
            status_code=500,
            detail="Server configuration error"
        )

    if not x_api_key:
        logger.warning("API request without API key")
        raise HTTPException(
            status_code=401,
            detail="Missing API key. Include X-API-Key header."
        )

    if x_api_key != expected_key:
        logger.warning(f"Invalid API key attempt: {x_api_key[:10]}...")
        raise HTTPException(
            status_code=401,
            detail="Invalid API key"
        )

    return x_api_key


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events"""
    # Startup
    logger.info("Starting Brand Zoning API")
    logger.info(f"OpenAI Model: {config.openai_model}")
    logger.info(f"Rules file loaded: {config.rules_file_exists}")

    if not config.rules_file_exists:
        logger.warning(f"Rules file not found at {config.system_rules_path}")

    yield

    # Shutdown
    logger.info("Shutting down Brand Zoning API")


app = FastAPI(
    title="Brand Zoning API",
    version="1.0.0",
    lifespan=lifespan
)

# Add rate limiter state
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=config.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class Assessment(RootModel[Dict[str, Any]]):
    """Brand architecture assessment data"""
    pass


@app.get("/")
def root():
    """API information endpoint"""
    return {
        "name": "Brand Zoning API",
        "version": "1.0.0",
        "description": "AI-powered brand architecture zone recommendations",
        "endpoints": {
            "POST /zone": "Generate zone recommendation from assessment",
            "GET /health": "Health check endpoint"
        }
    }


@app.get("/health")
def health():
    """Health check endpoint for monitoring"""
    return {
        "status": "healthy",
        "openai": "configured" if config.openai_api_key else "missing",
        "rules_loaded": config.rules_file_exists,
        "model": config.openai_model
    }


@app.get("/debug/prompts")
@limiter.limit("10/hour")
def debug_prompts(request: Request, api_key: str = Depends(verify_api_key)):
    """Debug endpoint to see the prompts being sent to OpenAI

    WARNING: This exposes your prompt engineering.
    Requires API key authentication.
    """
    rules_text = config.load_rules_text()

    return {
        "system_prompt": openai_service.system_prompt,
        "system_prompt_length": len(openai_service.system_prompt),
        "developer_prompt": openai_service.developer_prompt,
        "developer_prompt_length": len(openai_service.developer_prompt),
        "rules_file_loaded": config.rules_file_exists,
        "rules_file_length": len(rules_text),
        "rules_preview": rules_text[:500] + "..." if len(rules_text) > 500 else rules_text,
        "model": config.openai_model,
        "temperature": config.temperature
    }


@app.post("/zone")
@limiter.limit("50/hour")
def zone(request: Request, assessment: Assessment, api_key: str = Depends(verify_api_key)):
    """Generate zone recommendation report from assessment

    Requires API key authentication via X-API-Key header.
    Rate limited to 50 requests per hour per IP address.

    Args:
        request: FastAPI request object (for rate limiting)
        assessment: Brand architecture assessment JSON
        api_key: Verified API key from header

    Returns:
        Dict with report_markdown and summary

    Raises:
        HTTPException: 401 if invalid API key, 429 if rate limited, 503 on OpenAI errors
    """
    # Log request with brand info if available
    brand_name = assessment.root.get("brand", "Unknown")
    logger.info(f"📥 Received zone recommendation request for brand: {brand_name}")

    try:
        result = openai_service.generate_zone_report(assessment.root)

        # Log success with zone info
        zone = result.get("summary", {}).get("zone", "unknown")
        confidence = result.get("summary", {}).get("confidence", 0)
        logger.info(f"✅ Successfully generated zone recommendation: Zone {zone} ({confidence}% confidence)")

        return result

    except OpenAIServiceError as e:
        logger.error(f"❌ OpenAI service error for brand {brand_name}: {e}")
        raise HTTPException(
            status_code=503,
            detail=f"OpenAI service unavailable: {str(e)}"
        )
    except Exception as e:
        logger.error(f"❌ Unexpected error for brand {brand_name}: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Internal server error"
        )
