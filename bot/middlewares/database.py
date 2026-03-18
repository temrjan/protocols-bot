"""Database middleware - inject repositories into handlers."""

from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject

from bot.database import Database


class DatabaseMiddleware(BaseMiddleware):
    """Inject database repositories into handlers."""

    def __init__(self, db: Database) -> None:
        """Initialize middleware with database instance.

        Args:
            db: Database instance.
        """
        self.db = db

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        """Inject repositories into handler data.

        Args:
            handler: Handler function.
            event: Telegram event.
            data: Handler data dictionary.

        Returns:
            Handler result.
        """
        # Inject repository instances
        data["protocol_repo"] = self.db.protocols
        data["moderator_repo"] = self.db.moderators
        data["user_repo"] = self.db.users
        data["document_repo"] = self.db.documents

        return await handler(event, data)
