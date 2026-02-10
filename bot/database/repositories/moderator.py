"""Moderator repository for database operations."""

from bot.database.models import Moderator
from bot.database.repositories.base import BaseRepository


class ModeratorRepository(BaseRepository[Moderator]):
    """Repository for Moderator database operations.

    Provides methods for managing moderators.
    """

    async def list_moderators(self) -> list[int]:
        """List all moderator Telegram IDs.

        Returns:
            List of Telegram user IDs with moderator access.
        """
        rows = await self._fetch_all(
            "SELECT tg_user_id FROM moderators ORDER BY tg_user_id",
            tuple(),
        )
        return [row["tg_user_id"] for row in rows]

    async def add_moderator(self, tg_user_id: int) -> bool:
        """Add moderator by Telegram user ID.

        Args:
            tg_user_id: Telegram user ID.

        Returns:
            True if moderator was added, False if already exists.
        """
        try:
            await self.conn.execute(
                "INSERT INTO moderators (tg_user_id) VALUES (?)",
                (tg_user_id,),
            )
            await self.conn.commit()
            return True
        except Exception:
            await self.conn.rollback()
            return False

    async def is_moderator(self, tg_user_id: int) -> bool:
        """Check if user is a moderator.

        Args:
            tg_user_id: Telegram user ID.

        Returns:
            True if user is a moderator.
        """
        from bot.core import settings

        # Check if user is primary admin
        if tg_user_id == settings.PRIMARY_ADMIN_ID:
            return True

        # Check if user is in moderators table
        row = await self._fetch_one(
            "SELECT 1 FROM moderators WHERE tg_user_id = ?",
            (tg_user_id,),
        )
        return row is not None
