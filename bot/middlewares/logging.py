"""Logging middleware - structured event logging."""

from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject
from loguru import logger


class LoggingMiddleware(BaseMiddleware):
    """Structured logging middleware for Telegram events."""

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        """Log event information before processing.

        Args:
            handler: Handler function.
            event: Telegram event.
            data: Handler data dictionary.

        Returns:
            Handler result.
        """
        # Extract user ID if available
        user_id = None
        if hasattr(event, "from_user") and event.from_user:
            user_id = event.from_user.id

        # Log event
        event_type = type(event).__name__
        if user_id:
            logger.info("Event from user {}: {}", user_id, event_type)
        else:
            logger.info("Event: {}", event_type)

        # Process event
        try:
            result = await handler(event, data)
            return result
        except Exception as e:
            logger.error(
                "Error processing {} from user {}: {}",
                event_type,
                user_id,
                str(e),
            )
            raise
