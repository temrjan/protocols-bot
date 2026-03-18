"""Core application components."""

from bot.core.config import settings
from bot.core.loader import bot, dp
from bot.core.logging import setup_logging

__all__ = ["bot", "dp", "settings", "setup_logging"]
