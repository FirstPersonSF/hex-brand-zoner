import logging
import sys


def setup_logging(level: str = "INFO") -> None:
    """Configure structured logging for the application

    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR)
    """
    numeric_level = getattr(logging, level.upper(), logging.INFO)

    # Get root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(numeric_level)

    # Only add handler if none exist (preserves pytest's caplog handler)
    if not root_logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(numeric_level)
        formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
        handler.setFormatter(formatter)
        root_logger.addHandler(handler)
    else:
        # Update existing handlers' level
        for handler in root_logger.handlers:
            handler.setLevel(numeric_level)

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
    logger = logging.getLogger(name)
    return logger
