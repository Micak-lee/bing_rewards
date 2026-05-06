"""Structured logging to console and rotating file."""
import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

_logger: logging.Logger | None = None


def setup_logger(level: str = "INFO", log_file: Path = Path("rewards.log")) -> logging.Logger:
    """Create and configure the project-wide logger."""
    global _logger

    _logger = logging.getLogger("msrewards")
    _logger.setLevel(getattr(logging, level.upper(), logging.INFO))
    _logger.handlers.clear()

    fmt = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
    )

    console = logging.StreamHandler(sys.stdout)
    console.setFormatter(fmt)
    _logger.addHandler(console)

    file_handler = RotatingFileHandler(
        log_file, maxBytes=5 * 1024 * 1024, backupCount=3, encoding="utf-8"
    )
    file_handler.setFormatter(fmt)
    _logger.addHandler(file_handler)

    return _logger


def get_logger() -> logging.Logger:
    """Retrieve the configured logger."""
    if _logger is None:
        return setup_logger()
    return _logger
