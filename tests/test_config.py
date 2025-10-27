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


def test_config_parses_cors_origins_comma_separated(monkeypatch):
    """Config should parse comma-separated CORS origins"""
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-key-123")
    monkeypatch.setenv("CORS_ORIGINS", "http://localhost:3000,https://app.example.com,https://staging.example.com")

    config = Config()

    assert config.cors_origins == [
        "http://localhost:3000",
        "https://app.example.com",
        "https://staging.example.com"
    ]


def test_config_parses_cors_origins_with_whitespace(monkeypatch):
    """Config should handle whitespace in comma-separated CORS origins"""
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-key-123")
    monkeypatch.setenv("CORS_ORIGINS", " http://localhost:3000 , https://app.example.com , ")

    config = Config()

    assert config.cors_origins == [
        "http://localhost:3000",
        "https://app.example.com"
    ]


def test_config_parses_cors_origins_default_wildcard(monkeypatch):
    """Config should default to wildcard when CORS_ORIGINS not set"""
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-key-123")
    monkeypatch.delenv("CORS_ORIGINS", raising=False)

    config = Config()

    assert config.cors_origins == ["*"]


def test_config_parses_cors_origins_explicit_wildcard(monkeypatch):
    """Config should handle explicit wildcard CORS_ORIGINS"""
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-key-123")
    monkeypatch.setenv("CORS_ORIGINS", "*")

    config = Config()

    assert config.cors_origins == ["*"]


def test_config_loads_log_level_from_env(monkeypatch):
    """Config should load LOG_LEVEL from environment"""
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-key-123")
    monkeypatch.setenv("LOG_LEVEL", "DEBUG")

    config = Config()

    assert config.log_level == "DEBUG"


def test_config_uses_default_log_level(monkeypatch):
    """Config should default to INFO when LOG_LEVEL not set"""
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-key-123")
    monkeypatch.delenv("LOG_LEVEL", raising=False)

    config = Config()

    assert config.log_level == "INFO"
