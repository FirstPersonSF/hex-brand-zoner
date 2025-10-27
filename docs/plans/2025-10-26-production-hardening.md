# Brand Zoning API Production Hardening Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Transform the Brand Zoning API prototype into a production-ready service with comprehensive testing, robust error handling, proper configuration management, and Railway deployment readiness.

**Architecture:** Refactor monolithic `app.py` into modular components (config, OpenAI service, logging). Add retry logic, health checks, and structured error responses. Build comprehensive test suite with mocked and real OpenAI integration. Maintain backward compatibility with existing Replit app integration.

**Tech Stack:** FastAPI, OpenAI SDK, pytest, pytest-mock, python-json-logger, Railway

---

## Task 1: Configuration Management Module

**Files:**
- Create: `config.py`
- Test: `tests/test_config.py`

**Step 1: Write the failing test**

Create `tests/test_config.py`:

```python
import os
import pytest
from config import Config, ConfigError


def test_config_loads_from_environment(monkeypatch):
    """Config should load values from environment variables"""
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-key-123")
    monkeypatch.setenv("OPENAI_MODEL", "gpt-4o-mini")
    monkeypatch.setenv("SYSTEM_RULES_PATH", "/custom/rules.md")

    config = Config()

    assert config.openai_api_key == "sk-test-key-123"
    assert config.openai_model == "gpt-4o-mini"
    assert config.system_rules_path == "/custom/rules.md"


def test_config_uses_defaults_when_optional_vars_missing(monkeypatch):
    """Config should use defaults for optional environment variables"""
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-key-123")
    monkeypatch.delenv("OPENAI_MODEL", raising=False)
    monkeypatch.delenv("SYSTEM_RULES_PATH", raising=False)

    config = Config()

    assert config.openai_model == "gpt-4o"
    assert config.system_rules_path == "/app/rules/HEX-5112.md"


def test_config_validates_api_key_required(monkeypatch):
    """Config should raise error when OPENAI_API_KEY missing"""
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    with pytest.raises(ConfigError, match="OPENAI_API_KEY.*required"):
        Config()


def test_config_validates_rules_file_exists(monkeypatch, tmp_path):
    """Config should validate rules file exists and warn if missing"""
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-key-123")
    missing_path = tmp_path / "missing.md"
    monkeypatch.setenv("SYSTEM_RULES_PATH", str(missing_path))

    config = Config()

    assert config.rules_file_exists is False


def test_config_loads_rules_text(monkeypatch, tmp_path):
    """Config should load rules file content"""
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-key-123")
    rules_file = tmp_path / "rules.md"
    rules_file.write_text("# Test Rules\nRule 1: Always test")
    monkeypatch.setenv("SYSTEM_RULES_PATH", str(rules_file))

    config = Config()
    rules = config.load_rules_text()

    assert "Test Rules" in rules
    assert "Rule 1" in rules
```

**Step 2: Run test to verify it fails**

Run: `cd ~/.config/superpowers/worktrees/hex-brand-zoner/production-hardening && source .venv/bin/activate && pytest tests/test_config.py -v`

Expected: FAIL with "ModuleNotFoundError: No module named 'config'"

**Step 3: Write minimal implementation**

Create `config.py`:

```python
import os
from pathlib import Path
from typing import Optional


class ConfigError(Exception):
    """Raised when configuration is invalid"""
    pass


class Config:
    """Application configuration loaded from environment variables"""

    def __init__(self):
        # Required
        self.openai_api_key = self._get_required("OPENAI_API_KEY")

        # Optional with defaults
        self.openai_model = os.getenv("OPENAI_MODEL", "gpt-4o")
        self.system_rules_path = os.getenv(
            "SYSTEM_RULES_PATH",
            "/app/rules/HEX-5112.md"
        )
        self.log_level = os.getenv("LOG_LEVEL", "INFO")
        self.cors_origins = self._parse_cors_origins()

        # OpenAI client settings
        self.openai_timeout = 30.0
        self.openai_max_retries = 3
        self.temperature = 0.1

        # Validation
        self.rules_file_exists = Path(self.system_rules_path).exists()

    def _get_required(self, key: str) -> str:
        """Get required environment variable or raise ConfigError"""
        value = os.getenv(key)
        if not value:
            raise ConfigError(
                f"{key} environment variable is required but not set"
            )
        return value

    def _parse_cors_origins(self) -> list[str]:
        """Parse CORS_ORIGINS from comma-separated string"""
        origins = os.getenv("CORS_ORIGINS", "*")
        if origins == "*":
            return ["*"]
        return [o.strip() for o in origins.split(",") if o.strip()]

    def load_rules_text(self) -> str:
        """Load rules file content, return empty string if not found"""
        try:
            with open(self.system_rules_path, "r", encoding="utf-8") as f:
                return f.read()
        except FileNotFoundError:
            return ""
        except Exception as e:
            # Log but don't fail - rules file is optional
            return ""
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_config.py -v`

Expected: PASS (all 5 tests)

**Step 5: Commit**

```bash
git add config.py tests/test_config.py
git commit -m "feat: add configuration management with environment validation

- Load config from environment variables with validation
- Validate OPENAI_API_KEY is required
- Provide defaults for optional settings
- Check rules file existence
- Parse CORS origins from comma-separated list
- Add comprehensive unit tests

🤖 Generated with Claude Code
Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

## Task 2: Structured Logging Utility

**Files:**
- Create: `utils/logging_config.py`
- Test: `tests/test_logging.py`

**Step 1: Write the failing test**

Create `tests/test_logging.py`:

```python
import logging
import json
from utils.logging_config import setup_logging, get_logger


def test_setup_logging_configures_json_format():
    """setup_logging should configure JSON formatted logging"""
    setup_logging("DEBUG")
    logger = get_logger("test")

    assert logger.level == logging.DEBUG
    assert len(logger.handlers) > 0


def test_logger_includes_request_id(caplog):
    """Logger should support request_id in extra"""
    setup_logging("INFO")
    logger = get_logger("test")

    with caplog.at_level(logging.INFO):
        logger.info("test message", extra={"request_id": "req-123"})

    assert "test message" in caplog.text


def test_get_logger_returns_configured_logger():
    """get_logger should return properly configured logger"""
    logger = get_logger("api")

    assert logger.name == "api"
    assert isinstance(logger, logging.Logger)
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_logging.py -v`

Expected: FAIL with "ModuleNotFoundError: No module named 'utils'"

**Step 3: Write minimal implementation**

Create `utils/__init__.py` (empty file to make it a package):

```python
# Utils package
```

Create `utils/logging_config.py`:

```python
import logging
import sys
from typing import Optional


def setup_logging(level: str = "INFO") -> None:
    """Configure structured logging for the application

    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR)
    """
    numeric_level = getattr(logging, level.upper(), logging.INFO)

    # Configure root logger
    logging.basicConfig(
        level=numeric_level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)]
    )

    # Suppress noisy third-party loggers
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("openai").setLevel(logging.INFO)


def get_logger(name: str) -> logging.Logger:
    """Get a configured logger instance

    Args:
        name: Logger name (typically module name)

    Returns:
        Configured logger instance
    """
    return logging.getLogger(name)
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_logging.py -v`

Expected: PASS (all 3 tests)

**Step 5: Commit**

```bash
git add utils/__init__.py utils/logging_config.py tests/test_logging.py
git commit -m "feat: add structured logging configuration

- Set up consistent logging format across application
- Support configurable log levels
- Suppress noisy third-party loggers
- Add tests for logging configuration

🤖 Generated with Claude Code
Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

## Task 3: OpenAI Service Layer with Retry Logic

**Files:**
- Create: `services/__init__.py`
- Create: `services/openai_service.py`
- Test: `tests/test_openai_service.py`

**Step 1: Write the failing test**

Create `tests/test_openai_service.py`:

```python
import pytest
from unittest.mock import Mock, patch, MagicMock
from services.openai_service import OpenAIService, OpenAIServiceError
from config import Config


@pytest.fixture
def mock_config(monkeypatch, tmp_path):
    """Create mock config for testing"""
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-key")
    rules_file = tmp_path / "rules.md"
    rules_file.write_text("# Test Rules")
    monkeypatch.setenv("SYSTEM_RULES_PATH", str(rules_file))
    return Config()


def test_openai_service_initializes_with_config(mock_config):
    """OpenAIService should initialize with config"""
    service = OpenAIService(mock_config)

    assert service.config == mock_config
    assert service.client is not None


def test_generate_zone_report_success(mock_config):
    """generate_zone_report should return markdown and summary on success"""
    service = OpenAIService(mock_config)

    mock_response = Mock()
    mock_response.output_text = """# Zone 1 — Full Masterbrand Integration (Recommended)

**CONCLUSION:** Brand should integrate.

```json
{
  "brand": "Test Brand",
  "zone": "1",
  "zone_name": "Full Masterbrand Integration",
  "subzone": "A",
  "confidence": 85,
  "drivers": ["driver1"],
  "conflicts": [],
  "risks": ["risk1"],
  "next_steps": ["step1"]
}
```
"""

    with patch.object(service.client.responses, 'create', return_value=mock_response):
        result = service.generate_zone_report({"brand": "Test"})

    assert "Zone 1" in result["report_markdown"]
    assert result["summary"]["brand"] == "Test Brand"
    assert result["summary"]["zone"] == "1"


def test_generate_zone_report_retries_on_timeout(mock_config):
    """generate_zone_report should retry on timeout errors"""
    service = OpenAIService(mock_config)

    # First two calls timeout, third succeeds
    mock_response = Mock()
    mock_response.output_text = "# Zone 1\n```json\n{\"brand\":\"Test\",\"zone\":\"1\",\"zone_name\":\"Full Masterbrand Integration\",\"subzone\":\"A\",\"confidence\":80,\"drivers\":[],\"conflicts\":[],\"risks\":[],\"next_steps\":[]}\n```"

    with patch.object(service.client.responses, 'create') as mock_create:
        from openai import APITimeoutError
        mock_create.side_effect = [
            APITimeoutError("Timeout"),
            APITimeoutError("Timeout"),
            mock_response
        ]

        result = service.generate_zone_report({"brand": "Test"})

    assert mock_create.call_count == 3
    assert "Zone 1" in result["report_markdown"]


def test_generate_zone_report_fails_after_max_retries(mock_config):
    """generate_zone_report should raise error after max retries"""
    service = OpenAIService(mock_config)

    with patch.object(service.client.responses, 'create') as mock_create:
        from openai import APITimeoutError
        mock_create.side_effect = APITimeoutError("Timeout")

        with pytest.raises(OpenAIServiceError, match="OpenAI API call failed"):
            service.generate_zone_report({"brand": "Test"})

    assert mock_create.call_count == 3


def test_extract_summary_parses_json_from_markdown():
    """_extract_summary should parse JSON from markdown code fence"""
    from services.openai_service import _extract_summary

    markdown = """
# Report

Some text

```json
{
  "brand": "Test",
  "zone": "3"
}
```

More text
"""

    summary = _extract_summary(markdown)

    assert summary["brand"] == "Test"
    assert summary["zone"] == "3"


def test_extract_summary_returns_empty_dict_on_invalid_json():
    """_extract_summary should return empty dict if JSON invalid"""
    from services.openai_service import _extract_summary

    markdown = "No JSON here"
    summary = _extract_summary(markdown)

    assert summary == {}
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_openai_service.py -v`

Expected: FAIL with "ModuleNotFoundError: No module named 'services'"

**Step 3: Write minimal implementation**

Create `services/__init__.py`:

```python
# Services package
```

Create `services/openai_service.py`:

```python
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

    def generate_zone_report(self, assessment: Dict[str, Any]) -> Dict[str, Any]:
        """Generate zone recommendation report from assessment

        Args:
            assessment: Brand architecture assessment data

        Returns:
            Dict with 'report_markdown' and 'summary' keys

        Raises:
            OpenAIServiceError: If API call fails after retries
        """
        user_msg = (
            "ASSESSMENT JSON:\n" +
            json.dumps(assessment, ensure_ascii=False, indent=2) +
            "\n\nFollow all formatting + precedence rules exactly."
        )

        # Retry logic
        for attempt in range(self.config.openai_max_retries):
            try:
                logger.info(f"Calling OpenAI API (attempt {attempt + 1}/{self.config.openai_max_retries})")

                response = self.client.responses.create(
                    model=self.config.openai_model,
                    input=[
                        {"role": "system", "content": self.system_prompt},
                        {"role": "developer", "content": self.developer_prompt},
                        {"role": "user", "content": user_msg},
                    ],
                    text={
                        "format": {
                            "type": "json_schema",
                            "schema": self.MACHINE_JSON_SCHEMA
                        },
                        "require_json": False
                    },
                    temperature=self.config.temperature
                )

                markdown = response.output_text
                summary = _extract_summary(markdown)

                logger.info("Successfully generated zone report")
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
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_openai_service.py -v`

Expected: PASS (all 6 tests)

**Step 5: Commit**

```bash
git add services/ tests/test_openai_service.py
git commit -m "feat: add OpenAI service layer with retry logic

- Extract OpenAI integration into dedicated service
- Implement exponential backoff retry on timeouts
- Parse markdown and JSON summary from responses
- Move schema and prompts into service
- Add comprehensive tests with mocked API

🤖 Generated with Claude Code
Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

## Task 4: Refactor app.py to Use New Modules

**Files:**
- Modify: `app.py`
- Test: `tests/test_api.py`

**Step 1: Write the failing test**

Create `tests/test_api.py`:

```python
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, Mock


@pytest.fixture
def mock_env(monkeypatch, tmp_path):
    """Set up test environment"""
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-key")
    rules_file = tmp_path / "rules.md"
    rules_file.write_text("# Test Rules")
    monkeypatch.setenv("SYSTEM_RULES_PATH", str(rules_file))


def test_health_endpoint_returns_healthy(mock_env):
    """GET /health should return healthy status"""
    from app import app
    client = TestClient(app)

    response = client.get("/health")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "openai" in data
    assert "rules_loaded" in data


def test_root_endpoint_returns_api_info(mock_env):
    """GET / should return API information"""
    from app import app
    client = TestClient(app)

    response = client.get("/")

    assert response.status_code == 200
    data = response.json()
    assert "name" in data
    assert "version" in data


def test_zone_endpoint_requires_json_body(mock_env):
    """POST /zone should validate request body"""
    from app import app
    client = TestClient(app)

    response = client.post("/zone", json={})

    # Should accept empty dict (Assessment allows any keys)
    assert response.status_code in [200, 422, 500]


def test_zone_endpoint_returns_report_and_summary(mock_env):
    """POST /zone should return markdown report and summary"""
    from app import app
    client = TestClient(app)

    mock_result = {
        "report_markdown": "# Zone 1\nReport content",
        "summary": {"brand": "Test", "zone": "1"}
    }

    with patch("app.openai_service.generate_zone_report", return_value=mock_result):
        response = client.post("/zone", json={"brand": "Test Brand"})

    assert response.status_code == 200
    data = response.json()
    assert "report_markdown" in data
    assert "summary" in data
    assert data["summary"]["brand"] == "Test"


def test_zone_endpoint_handles_openai_errors(mock_env):
    """POST /zone should return 503 on OpenAI service errors"""
    from app import app
    from services.openai_service import OpenAIServiceError
    client = TestClient(app)

    with patch("app.openai_service.generate_zone_report", side_effect=OpenAIServiceError("API failed")):
        response = client.post("/zone", json={"brand": "Test"})

    assert response.status_code == 503
    assert "OpenAI service unavailable" in response.json()["detail"]
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_api.py -v`

Expected: FAIL with various errors (endpoints don't exist, modules not imported)

**Step 3: Write minimal implementation**

Modify `app.py`:

```python
import os
from typing import Any, Dict
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
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


class Assessment(BaseModel):
    """Brand architecture assessment data"""
    __root__: Dict[str, Any]


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
    logger.info("Received zone recommendation request")

    try:
        result = openai_service.generate_zone_report(assessment.__root__)
        logger.info("Successfully generated zone recommendation")
        return result

    except OpenAIServiceError as e:
        logger.error(f"OpenAI service error: {e}")
        raise HTTPException(
            status_code=503,
            detail=f"OpenAI service unavailable: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Internal server error"
        )
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_api.py -v`

Expected: PASS (all 5 tests)

**Step 5: Commit**

```bash
git add app.py tests/test_api.py
git commit -m "refactor: modularize app.py with new components

- Import and use Config, OpenAIService, logging
- Add health check and root info endpoints
- Add lifespan events for startup/shutdown logging
- Improve error handling with structured responses
- Remove hardcoded prompts and client initialization
- Add comprehensive API endpoint tests

🤖 Generated with Claude Code
Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

## Task 5: Add Input Validation Tests

**Files:**
- Test: `tests/test_validation.py`

**Step 1: Write the test**

Create `tests/test_validation.py`:

```python
import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def mock_env(monkeypatch, tmp_path):
    """Set up test environment"""
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-key")
    rules_file = tmp_path / "rules.md"
    rules_file.write_text("# Test Rules")
    monkeypatch.setenv("SYSTEM_RULES_PATH", str(rules_file))


def test_zone_accepts_empty_assessment(mock_env):
    """POST /zone should accept empty assessment dict"""
    from app import app
    from unittest.mock import patch
    client = TestClient(app)

    mock_result = {
        "report_markdown": "# Zone 1",
        "summary": {"brand": "Unknown", "zone": "1", "zone_name": "Full Masterbrand Integration",
                   "subzone": "A", "confidence": 50, "drivers": [], "conflicts": [],
                   "risks": [], "next_steps": []}
    }

    with patch("app.openai_service.generate_zone_report", return_value=mock_result):
        response = client.post("/zone", json={})

    assert response.status_code == 200


def test_zone_accepts_complex_nested_assessment(mock_env):
    """POST /zone should accept deeply nested assessment structures"""
    from app import app
    from unittest.mock import patch
    client = TestClient(app)

    complex_assessment = {
        "brand": "Test",
        "zone1": {"field": "value", "nested": {"deep": "data"}},
        "zone2": {"array": [1, 2, 3]},
        "metadata": {"user": "test", "timestamp": "2025-10-26"}
    }

    mock_result = {
        "report_markdown": "# Zone 3",
        "summary": {"brand": "Test", "zone": "3", "zone_name": "Endorsed Brand",
                   "subzone": "B", "confidence": 75, "drivers": [], "conflicts": [],
                   "risks": [], "next_steps": []}
    }

    with patch("app.openai_service.generate_zone_report", return_value=mock_result):
        response = client.post("/zone", json=complex_assessment)

    assert response.status_code == 200


def test_zone_rejects_non_json_body(mock_env):
    """POST /zone should reject non-JSON request bodies"""
    from app import app
    client = TestClient(app)

    response = client.post("/zone", data="not json")

    assert response.status_code == 422


def test_zone_rejects_json_array(mock_env):
    """POST /zone should reject JSON array (expects object)"""
    from app import app
    client = TestClient(app)

    response = client.post("/zone", json=["array", "not", "object"])

    assert response.status_code == 422
```

**Step 2: Run test to verify it passes**

Run: `pytest tests/test_validation.py -v`

Expected: PASS (all 4 tests)

**Step 3: Commit**

```bash
git add tests/test_validation.py
git commit -m "test: add input validation tests for /zone endpoint

- Test empty assessment handling
- Test complex nested structures
- Test non-JSON body rejection
- Test array rejection (expects object)

🤖 Generated with Claude Code
Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

## Task 6: Add Parsing Tests

**Files:**
- Test: `tests/test_parsing.py`

**Step 1: Write the test**

Create `tests/test_parsing.py`:

```python
import pytest
from services.openai_service import _extract_summary


def test_extract_summary_with_valid_json():
    """Should extract JSON from properly formatted markdown"""
    markdown = """# Zone 1 — Full Masterbrand Integration

**CONCLUSION:** Integration recommended.

```json
{
  "brand": "TestBrand",
  "zone": "1",
  "zone_name": "Full Masterbrand Integration",
  "subzone": "A",
  "confidence": 90,
  "drivers": ["driver1", "driver2"],
  "conflicts": [],
  "risks": ["risk1"],
  "next_steps": ["step1", "step2"]
}
```

Additional text.
"""

    result = _extract_summary(markdown)

    assert result["brand"] == "TestBrand"
    assert result["zone"] == "1"
    assert result["confidence"] == 90
    assert len(result["drivers"]) == 2
    assert len(result["next_steps"]) == 2


def test_extract_summary_with_whitespace_in_fence():
    """Should handle extra whitespace around JSON fence"""
    markdown = """
Some content

```json

{
  "brand": "Test",
  "zone": "3"
}

```

More content
"""

    result = _extract_summary(markdown)

    assert result["brand"] == "Test"
    assert result["zone"] == "3"


def test_extract_summary_returns_empty_dict_when_no_json():
    """Should return empty dict when no JSON fence found"""
    markdown = "# Report\nNo JSON here"

    result = _extract_summary(markdown)

    assert result == {}


def test_extract_summary_returns_empty_dict_on_malformed_json():
    """Should return empty dict when JSON is malformed"""
    markdown = """
```json
{
  "brand": "Test"
  "zone": "missing comma"
}
```
"""

    result = _extract_summary(markdown)

    assert result == {}


def test_extract_summary_handles_multiple_json_blocks():
    """Should extract first JSON block when multiple present"""
    markdown = """
```json
{"brand": "First", "zone": "1"}
```

```json
{"brand": "Second", "zone": "2"}
```
"""

    result = _extract_summary(markdown)

    # Should get first block
    assert result["brand"] == "First"
    assert result["zone"] == "1"
```

**Step 2: Run test to verify it passes**

Run: `pytest tests/test_parsing.py -v`

Expected: PASS (all 5 tests)

**Step 3: Commit**

```bash
git add tests/test_parsing.py
git commit -m "test: add comprehensive parsing tests

- Test valid JSON extraction from markdown
- Test whitespace handling in code fences
- Test missing JSON handling
- Test malformed JSON handling
- Test multiple JSON blocks

🤖 Generated with Claude Code
Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

## Task 7: Update Requirements with Test Dependencies

**Files:**
- Modify: `requirements.txt`

**Step 1: Update requirements.txt**

Modify `requirements.txt`:

```txt
# Production dependencies
fastapi
uvicorn[standard]
openai>=1.40.0
pydantic

# Testing dependencies
pytest>=7.0.0
pytest-mock>=3.10.0
pytest-cov>=4.0.0
httpx>=0.24.0
```

**Step 2: Install new dependencies**

Run: `source .venv/bin/activate && pip install -r requirements.txt`

Expected: pytest and related packages install successfully

**Step 3: Verify all tests pass**

Run: `pytest -v`

Expected: All tests PASS

**Step 4: Commit**

```bash
git add requirements.txt
git commit -m "build: add testing dependencies to requirements

- Add pytest for test framework
- Add pytest-mock for mocking utilities
- Add pytest-cov for coverage reporting
- Add httpx for FastAPI test client

🤖 Generated with Claude Code
Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

## Task 8: Add Integration Test with Sample Data

**Files:**
- Test: `tests/test_integration.py`

**Step 1: Write the test**

Create `tests/test_integration.py`:

```python
import pytest
from fastapi.testclient import TestClient
from pathlib import Path
import json


@pytest.fixture
def mock_env(monkeypatch):
    """Set up test environment with real rules file"""
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-key")
    # Use actual rules file from project
    rules_path = Path(__file__).parent.parent / "rules" / "HEX 5112 - Brand Architecture - Full Set of Questions & Logic Scoring v009.md"
    if rules_path.exists():
        monkeypatch.setenv("SYSTEM_RULES_PATH", str(rules_path))


@pytest.fixture
def sample_assessment():
    """Load sample assessment from samples directory"""
    sample_path = Path(__file__).parent.parent / "samples" / "novatel_assessment.json"
    with open(sample_path, "r") as f:
        return json.load(f)


def test_zone_endpoint_with_sample_assessment(mock_env, sample_assessment):
    """POST /zone should process actual sample assessment"""
    from app import app
    from unittest.mock import patch, Mock
    client = TestClient(app)

    # Mock OpenAI response with realistic data
    mock_response = Mock()
    mock_response.output_text = """# Zone 1 — Full Masterbrand Integration (Recommended)

**CONCLUSION:** Based on the assessment data, NovAtel should pursue full integration into the Hexagon masterbrand.

**Confidence: 75/100**
- Evidence strength: 30/40
- Data completeness: 25/30
- Conflict resolution: 20/30

**Zone-Specific Assessment**
The brand shows strong indicators for masterbrand integration with limited market awareness outside current territories.

**Strategic Recommendations**
- Begin phased integration over 12-month period
- Leverage Hexagon's positioning in autonomy markets

**Risk Analysis & Mitigation**
- Monitor customer awareness during transition
- Address potential confusion in legacy markets

**Next Steps & Action Items**
1. Develop detailed integration roadmap
2. Communicate changes to key stakeholders
3. Update digital presence and materials

**Machine-Readable Summary**
```json
{
  "brand": "NovAtel",
  "zone": "1",
  "zone_name": "Full Masterbrand Integration",
  "subzone": "A",
  "confidence": 75,
  "drivers": ["Low independent awareness", "Partially embedded"],
  "conflicts": ["Legacy presence in some regions"],
  "risks": ["Customer confusion during transition"],
  "next_steps": ["Develop integration roadmap", "Stakeholder communication"]
}
```
"""

    with patch("app.openai_service.client.responses.create", return_value=mock_response):
        response = client.post("/zone", json=sample_assessment)

    assert response.status_code == 200
    data = response.json()

    # Verify structure
    assert "report_markdown" in data
    assert "summary" in data

    # Verify summary content
    summary = data["summary"]
    assert summary["brand"] == "NovAtel"
    assert summary["zone"] in ["1", "3", "4", "5"]
    assert "zone_name" in summary
    assert "confidence" in summary
    assert isinstance(summary["drivers"], list)
    assert isinstance(summary["next_steps"], list)


def test_health_check_with_real_config(mock_env):
    """GET /health should return accurate status with real config"""
    from app import app
    client = TestClient(app)

    response = client.get("/health")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["openai"] == "configured"
    assert data["model"] == "gpt-4o"
```

**Step 2: Run test to verify it passes**

Run: `pytest tests/test_integration.py -v`

Expected: PASS (all 2 tests)

**Step 3: Commit**

```bash
git add tests/test_integration.py
git commit -m "test: add integration tests with sample data

- Test /zone endpoint with real sample assessment
- Test health check with actual configuration
- Verify response structure and content
- Use mocked OpenAI to avoid API costs

🤖 Generated with Claude Code
Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

## Task 9: Add Test Configuration File

**Files:**
- Create: `pytest.ini`
- Create: `tests/__init__.py`

**Step 1: Create pytest configuration**

Create `pytest.ini`:

```ini
[pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts =
    -v
    --strict-markers
    --tb=short
    --cov=.
    --cov-report=term-missing
    --cov-report=html
    --cov-config=.coveragerc
markers =
    integration: Integration tests (may be slower)
    unit: Fast unit tests
```

Create `.coveragerc`:

```ini
[run]
source = .
omit =
    */tests/*
    */.venv/*
    */venv/*
    */__pycache__/*
    */site-packages/*
    setup.py

[report]
exclude_lines =
    pragma: no cover
    def __repr__
    raise AssertionError
    raise NotImplementedError
    if __name__ == .__main__.:
    if TYPE_CHECKING:
```

Create `tests/__init__.py` (empty file):

```python
# Tests package
```

**Step 2: Run tests with coverage**

Run: `pytest --cov=. --cov-report=term-missing`

Expected: Tests run with coverage report showing >80% coverage

**Step 3: Commit**

```bash
git add pytest.ini .coveragerc tests/__init__.py
git commit -m "test: add pytest configuration and coverage settings

- Configure pytest with sensible defaults
- Set up coverage reporting (terminal + HTML)
- Add test markers for unit vs integration
- Exclude virtual env and cache from coverage

🤖 Generated with Claude Code
Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

## Task 10: Update .gitignore for Test Artifacts

**Files:**
- Modify: `.gitignore`

**Step 1: Update .gitignore**

Modify `.gitignore`:

```
__pycache__/
*.pyc
.env
.venv
venv/
.DS_Store
.idea
.vscode

# Test artifacts
.pytest_cache/
.coverage
htmlcov/
*.cover
.hypothesis/

# Build artifacts
*.egg-info/
dist/
build/
```

**Step 2: Commit**

```bash
git add .gitignore
git commit -m "chore: update gitignore for test artifacts

- Ignore pytest cache
- Ignore coverage reports
- Ignore build artifacts
- Ignore hypothesis test data

🤖 Generated with Claude Code
Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

## Task 11: Update Railway Configuration

**Files:**
- Modify: `Railway.toml`

**Step 1: Update Railway.toml**

Modify `Railway.toml`:

```toml
[build]
builder = "NIXPACKS"

[deploy]
startCommand = "uvicorn app:app --host 0.0.0.0 --port ${PORT}"
restartPolicyType = "on_failure"
healthcheckPath = "/health"
healthcheckTimeout = 10

[variables]
OPENAI_MODEL = "gpt-4o"
SYSTEM_RULES_PATH = "/app/rules/HEX 5112 - Brand Architecture - Full Set of Questions & Logic Scoring v009.md"
LOG_LEVEL = "INFO"
```

**Step 2: Commit**

```bash
git add Railway.toml
git commit -m "config: update Railway deployment configuration

- Add health check endpoint path
- Set health check timeout to 10s
- Add LOG_LEVEL environment variable
- Use full rules file name in path

🤖 Generated with Claude Code
Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

## Task 12: Update README with New Features

**Files:**
- Modify: `README.md`

**Step 1: Update README**

Modify `README.md`:

```markdown
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
```

**Step 2: Commit**

```bash
git add README.md
git commit -m "docs: update README with production features

- Document new health check and info endpoints
- Add testing instructions
- Update deployment guide with new env vars
- Add project structure overview
- Document configuration options
- Add security recommendations

🤖 Generated with Claude Code
Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

## Task 13: Final Verification

**Step 1: Run full test suite**

Run: `pytest -v --cov=. --cov-report=term-missing`

Expected: All tests PASS with >80% coverage

**Step 2: Verify app starts locally**

Run: `export OPENAI_API_KEY=sk-test && uvicorn app:app --port 8080`

Expected: App starts without errors, logs show "Starting Brand Zoning API"

**Step 3: Test endpoints manually**

Run in separate terminal:
```bash
# Health check
curl http://localhost:8080/health

# API info
curl http://localhost:8080/
```

Expected: Both return 200 OK with JSON responses

**Step 4: Review changes**

Run: `git log --oneline -13`

Expected: 13 commits showing all completed tasks

---

## Deployment to Railway

After all tasks complete:

**Step 1: Push to GitHub**

```bash
git push origin feature/production-hardening
```

**Step 2: Create Pull Request** (optional, or merge directly to main)

**Step 3: Railway Setup**

1. Go to Railway dashboard
2. New Project → Deploy from GitHub
3. Select `hex-brand-zoner` repository
4. Select `feature/production-hardening` branch (or main after merge)
5. Add environment variables:
   - `OPENAI_API_KEY` = your actual OpenAI key
   - `OPENAI_MODEL` = `gpt-4o`
   - `SYSTEM_RULES_PATH` = `/app/rules/HEX 5112 - Brand Architecture - Full Set of Questions & Logic Scoring v009.md`
   - `LOG_LEVEL` = `INFO`
   - `CORS_ORIGINS` = `https://your-replit-app-url.repl.co`
6. Deploy

**Step 4: Verify Deployment**

```bash
# Replace with your Railway URL
RAILWAY_URL="https://your-service.up.railway.app"

# Test health check
curl $RAILWAY_URL/health

# Test with sample data
curl -X POST $RAILWAY_URL/zone \
  -H "Content-Type: application/json" \
  -d @samples/novatel_assessment.json
```

**Step 5: Update Replit App**

Update your Replit app to use the Railway URL for API calls.

---

## Success Criteria

- [x] All 13 tasks completed
- [x] All tests passing (>80% coverage)
- [x] Health check endpoint operational
- [x] Configuration loaded from environment
- [x] OpenAI service with retry logic
- [x] Structured logging implemented
- [x] Error handling comprehensive
- [x] Documentation updated
- [x] Railway configuration ready
- [x] Backward compatible with Replit app

---

## Troubleshooting

**Import errors:**
- Ensure you're in the worktree directory
- Activate virtual environment: `source .venv/bin/activate`

**Tests failing:**
- Check OPENAI_API_KEY is set in test environment
- Verify rules file path is correct
- Run `pytest -v` for detailed error messages

**App won't start:**
- Check OPENAI_API_KEY environment variable is set
- Verify all dependencies installed: `pip install -r requirements.txt`
- Check logs for configuration errors

**Railway deployment fails:**
- Verify all environment variables set in Railway dashboard
- Check Railway logs for startup errors
- Ensure rules file exists in repository
