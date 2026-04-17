"""Throttling middleware - anti-flood protection."""

import contextlib
from collections.abc import Awaitable, Callable
from datetime import datetime, timedelta
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message, TelegramObject
from loguru import logger


class ThrottlingMiddleware(BaseMiddleware):
    """Anti-flood middleware with rate limiting.

    Limits the rate of incoming messages and callback queries (1 event per
    second per user by default). Register a separate instance for each event
    type so the cooldowns remain independent.
    """

    def __init__(self, rate_limit: float = 1.0) -> None:
        """Initialize throttling middleware.

        Args:
            rate_limit: Minimum seconds between events from the same user.
        """
        self.rate_limit = rate_limit
        self.user_last: dict[int, datetime] = {}

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        """Check rate limit before processing event.

        Args:
            handler: Handler function.
            event: Telegram event.
            data: Handler data dictionary.

        Returns:
            Handler result or None if throttled.
        """
        # Only throttle messages and callback queries
        if not isinstance(event, (Message, CallbackQuery)):
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
                    "User {} throttled ({}s since last event)",
                    user_id,
                    delta,
                )
                # Acknowledge callback to clear the spinner; ignore stale callbacks.
                if isinstance(event, CallbackQuery):
                    with contextlib.suppress(Exception):
                        await event.answer()
                return None

        # Update last message time
        self.user_last[user_id] = now

        # Clean up old entries (older than 1 hour)
        cutoff = now - timedelta(hours=1)
        self.user_last = {uid: ts for uid, ts in self.user_last.items() if ts > cutoff}

        return await handler(event, data)
