"""Admin and moderator access filters."""

from aiogram.filters import BaseFilter
from aiogram.types import CallbackQuery, Message

from bot.core.config import settings


class IsAdmin(BaseFilter):
    """Check if user is admin."""

    async def __call__(self, event: Message | CallbackQuery) -> bool:
        """Check if user is in admin list.

        Args:
            event: Message or callback query.

        Returns:
            True if user is admin.
        """
        if not event.from_user:
            return False
        return event.from_user.id in settings.admin_ids


class IsModerator(BaseFilter):
    """Check if user is moderator (can upload protocols)."""

    async def __call__(
        self,
        event: Message | CallbackQuery,
        moderator_repo,  # Injected by middleware
    ) -> bool:
        """Check if user is admin or moderator.

        Args:
            event: Message or callback query.
            moderator_repo: Moderator repository (injected by middleware).

        Returns:
            True if user is admin or moderator.
        """
        if not event.from_user:
            return False

        # Check if admin
        if event.from_user.id in settings.admin_ids:
            return True

        # Check if moderator
        return await moderator_repo.is_moderator(event.from_user.id)
