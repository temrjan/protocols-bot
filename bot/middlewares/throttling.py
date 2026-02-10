"""Throttling middleware - anti-flood protection."""

from datetime import datetime, timedelta
from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.types import Message, TelegramObject
from loguru import logger


class ThrottlingMiddleware(BaseMiddleware):
    """Anti-flood middleware with rate limiting.

    Limits message rate to prevent spam (1 message per second per user by default).
    """

    def __init__(self, rate_limit: float = 1.0) -> None:
        """Initialize throttling middleware.

        Args:
            rate_limit: Minimum seconds between messages from same user.
        """
        self.rate_limit = rate_limit
        self.user_last: dict[int, datetime] = {}

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        """Check rate limit before processing message.

        Args:
            handler: Handler function.
            event: Telegram event.
            data: Handler data dictionary.

        Returns:
            Handler result or None if throttled.
        """
        # Only throttle messages
        if not isinstance(event, Message):
            return await handler(event, data)

        user_id = event.from_user.id if event.from_user else None
        if user_id is None:
            return await handler(event, data)

        now = datetime.now()
        last_time = self.user_last.get(user_id)

        # Check if user is throttled
        if last_time is not None:
            delta = (now - last_time).total_seconds()
            if delta < self.rate_limit:
                logger.warning(
                    "User {} throttled ({}s since last message)",
                    user_id,
                    delta,
                )
                # Silently ignore throttled messages
                return None

        # Update last message time
        self.user_last[user_id] = now

        # Clean up old entries (older than 1 hour)
        cutoff = now - timedelta(hours=1)
        self.user_last = {
            uid: ts for uid, ts in self.user_last.items() if ts > cutoff
        }

        return await handler(event, data)
