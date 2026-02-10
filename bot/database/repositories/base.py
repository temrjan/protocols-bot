"""Base repository with common database operations."""

from typing import Any, Generic, TypeVar

import aiosqlite

T = TypeVar("T")


class BaseRepository(Generic[T]):
    """Base repository with common database operations.

    Args:
        conn: aiosqlite connection.
    """

    def __init__(self, conn: aiosqlite.Connection) -> None:
        """Initialize repository with database connection."""
        self.conn = conn

    async def _fetch_all(
        self, query: str, params: tuple[Any, ...] = ()
    ) -> list[aiosqlite.Row]:
        """Fetch all rows from query.

        Args:
            query: SQL query.
            params: Query parameters.

        Returns:
            List of rows.
        """
        cursor = await self.conn.execute(query, params)
        rows = await cursor.fetchall()
        await cursor.close()
        return rows

    async def _fetch_one(
        self, query: str, params: tuple[Any, ...] = ()
    ) -> aiosqlite.Row | None:
        """Fetch one row from query.

        Args:
            query: SQL query.
            params: Query parameters.

        Returns:
            Row or None if not found.
        """
        cursor = await self.conn.execute(query, params)
        row = await cursor.fetchone()
        await cursor.close()
        return row
