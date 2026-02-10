"""User repository for database operations."""

from bot.database.models import User
from bot.database.repositories.base import BaseRepository


class UserRepository(BaseRepository[User]):
    """Repository for User database operations.

    Provides methods for user settings management.
    """

    async def get_user_lang(self, tg_user_id: int) -> str | None:
        """Get user language preference.

        Args:
            tg_user_id: Telegram user ID.

        Returns:
            Language code ('ru' or 'uz') or None if user not found.
        """
        row = await self._fetch_one(
            "SELECT lang FROM users WHERE tg_user_id = ?",
            (tg_user_id,),
        )
        return row["lang"] if row else None

    async def set_user_lang(self, tg_user_id: int, lang: str) -> None:
        """Set user language preference.

        Args:
            tg_user_id: Telegram user ID.
            lang: Language code ('ru' or 'uz').
        """
        await self.conn.execute(
            """
            INSERT INTO users (tg_user_id, lang) VALUES (?, ?)
            ON CONFLICT(tg_user_id) DO UPDATE SET lang = excluded.lang
            """,
            (tg_user_id, lang),
        )
        await self.conn.commit()

    async def get_lang(self, tg_user_id: int) -> str | None:
        """Alias for get_user_lang for convenience.

        Args:
            tg_user_id: Telegram user ID.

        Returns:
            Language code ('ru' or 'uz') or None if user not found.
        """
        return await self.get_user_lang(tg_user_id)

    async def set_lang(self, tg_user_id: int, lang: str) -> None:
        """Alias for set_user_lang for convenience.

        Args:
            tg_user_id: Telegram user ID.
            lang: Language code ('ru' or 'uz').
        """
        await self.set_user_lang(tg_user_id, lang)
