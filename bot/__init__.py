"""Protocols Bot - Telegram bot for managing laboratory protocols."""

__version__ = "2.0.0"
__author__ = "Claude Code"
__description__ = "Refactored protocols bot with modular architecture"

from bot.core import settings, bot, dp
from bot.database import Database

__all__ = ["settings", "bot", "dp", "Database"]
