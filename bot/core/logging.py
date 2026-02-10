"""Logging configuration using loguru."""

import sys
from pathlib import Path

from loguru import logger


def setup_logging(level: str = "INFO") -> None:
    """Configure loguru logging.

    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR).
    """
    log_path = Path("logs/bot.log")
    log_path.parent.mkdir(exist_ok=True)

    logger.remove()  # Remove default handler
    logger.add(sys.stderr, level=level)
    logger.add(
        log_path,
        rotation="10 MB",
        retention="14 days",
        level=level,
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
    )
