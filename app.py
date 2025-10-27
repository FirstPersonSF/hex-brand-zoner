import os
from typing import Any, Dict
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import RootModel
from contextlib import asynccontextmanager

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
def debug_prompts():
    """Debug endpoint to see the prompts being sent to OpenAI

    WARNING: This exposes your prompt engineering.
    Remove or protect this endpoint in production.
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
def zone(assessment: Assessment):
    """Generate zone recommendation report from assessment

    Args:
        assessment: Brand architecture assessment JSON

    Returns:
        Dict with report_markdown and summary

    Raises:
        HTTPException: On service errors
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
