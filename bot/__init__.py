"""Protocols Bot - Telegram bot for managing laboratory protocols."""

__version__ = "2.0.0"
__author__ = "Claude Code"
__description__ = "Refactored protocols bot with modular architecture"

from bot.core import bot, dp, settings
from bot.database import Database

__all__ = ["Database", "bot", "dp", "settings"]
