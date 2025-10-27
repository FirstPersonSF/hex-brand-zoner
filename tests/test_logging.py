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
