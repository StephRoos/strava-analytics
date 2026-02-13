"""Centralized logging configuration."""

import logging
import sys
from pathlib import Path
from typing import Optional
from config.settings import settings

# Logging configuration
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

# Log directory
LOG_DIR = Path(__file__).parent.parent / "logs"
LOG_DIR.mkdir(exist_ok=True)


def get_log_level(level_name: str) -> int:
    """Convert log level name to logging constant."""
    levels = {
        "DEBUG": logging.DEBUG,
        "INFO": logging.INFO,
        "WARNING": logging.WARNING,
        "ERROR": logging.ERROR,
        "CRITICAL": logging.CRITICAL,
    }
    return levels.get(level_name.upper(), logging.INFO)


def setup_logger(
    name: str,
    level: Optional[str] = None,
    log_file: Optional[str] = None
) -> logging.Logger:
    """
    Configure and return a logger instance.

    Args:
        name: Logger name (typically module name)
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Optional file path for file logging

    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)

    # Set log level
    log_level = get_log_level(level or settings.LOG_LEVEL)
    logger.setLevel(log_level)

    # Avoid duplicate handlers
    if logger.handlers:
        return logger

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    console_formatter = logging.Formatter(LOG_FORMAT, LOG_DATE_FORMAT)
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)

    # File handler (if specified or in production)
    if log_file or not settings.DEBUG:
        file_path = LOG_DIR / (log_file or f"{settings.APP_NAME.lower().replace(' ', '_')}.log")
        file_handler = logging.FileHandler(file_path, encoding="utf-8")
        file_handler.setLevel(log_level)
        file_formatter = logging.Formatter(LOG_FORMAT, LOG_DATE_FORMAT)
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)

    # Prevent propagation to root logger
    logger.propagate = False

    return logger


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance for a module.

    Args:
        name: Logger name (use __name__ in calling module)

    Returns:
        Configured logger instance

    Example:
        >>> from utils.logger import get_logger
        >>> logger = get_logger(__name__)
        >>> logger.info("Application started")
    """
    return setup_logger(name)


# Create default application logger
app_logger = get_logger("strava_analytics")


def log_exception(logger: logging.Logger, exc: Exception, context: str = ""):
    """
    Log an exception with context.

    Args:
        logger: Logger instance
        exc: Exception to log
        context: Additional context information
    """
    if context:
        logger.error(f"{context}: {type(exc).__name__}: {str(exc)}", exc_info=True)
    else:
        logger.error(f"{type(exc).__name__}: {str(exc)}", exc_info=True)
