import logging
from utils.logging_config import setup_logging, get_logger


def test_setup_logging_configures_text_format():
    """setup_logging should configure text formatted logging"""
    setup_logging("DEBUG")
    logger = get_logger("test")

    # Check that root logger is configured with DEBUG level
    root_logger = logging.getLogger()
    assert root_logger.level == logging.DEBUG
    assert len(root_logger.handlers) > 0


def test_logger_includes_request_id(caplog):
    """Logger should accept request_id in extra without errors"""
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
