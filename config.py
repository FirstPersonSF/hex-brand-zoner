import os
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


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
            # Expected case when rules file is not present
            logger.debug(
                f"Rules file not found at {self.system_rules_path}, "
                "using empty rules"
            )
            return ""
        except Exception as e:
            # Unexpected errors (permissions, encoding, etc.)
            logger.warning(
                f"Failed to load rules file from {self.system_rules_path}: {e}",
                exc_info=True
            )
            return ""
