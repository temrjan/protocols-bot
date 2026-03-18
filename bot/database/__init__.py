"""Database module with connection management and repository access."""

from __future__ import annotations

import aiosqlite
from loguru import logger

from bot.database.repositories import (
    DocumentRepository,
    ModeratorRepository,
    ProtocolRepository,
    UserRepository,
)


class Database:
    """Database connection manager with repository access.

    Attributes:
        protocols: Protocol repository instance.
        moderators: Moderator repository instance.
        users: User repository instance.
        documents: Document repository instance.
    """

    def __init__(self, path: str) -> None:
        """Initialize database with path.

        Args:
            path: SQLite database file path.
        """
        self._path = path
        self._conn: aiosqlite.Connection | None = None
        self.protocols: ProtocolRepository | None = None
        self.moderators: ModeratorRepository | None = None
        self.users: UserRepository | None = None
        self.documents: DocumentRepository | None = None

    async def connect(self) -> None:
        """Connect to database and initialize repositories."""
        if self._conn is None:
            self._conn = await aiosqlite.connect(self._path)
            self._conn.row_factory = aiosqlite.Row
            logger.debug("SQLite connection opened at {}", self._path)
            await self._ensure_schema()
            # Initialize repositories
            self.protocols = ProtocolRepository(self._conn)
            self.moderators = ModeratorRepository(self._conn)
            self.users = UserRepository(self._conn)
            self.documents = DocumentRepository(self._conn)

    async def close(self) -> None:
        """Close database connection."""
        if self._conn is not None:
            await self._conn.close()
            self._conn = None
            self.protocols = None
            self.moderators = None
            self.users = None
            self.documents = None
            logger.debug("SQLite connection closed")

    async def _ensure_schema(self) -> None:
        """Ensure database schema exists."""
        if self._conn is None:
            raise RuntimeError("Database connection not initialized")

        await self._conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS protocols (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              year INTEGER NOT NULL,
              product TEXT NOT NULL,
              protocol_no TEXT NOT NULL,
              batch_no TEXT NOT NULL DEFAULT 'N/A',
              version INTEGER NOT NULL DEFAULT 1,
              storage_key TEXT NOT NULL,
              filename TEXT NOT NULL,
              size_bytes INTEGER,
              mime TEXT DEFAULT 'application/pdf',
              tg_file_id TEXT,
              is_active INTEGER DEFAULT 1,
              uploaded_by INTEGER,
              uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE INDEX IF NOT EXISTS idx_protocols_lookup ON protocols(year, product, protocol_no);
            CREATE INDEX IF NOT EXISTS idx_protocols_active ON protocols(is_active);

            CREATE TABLE IF NOT EXISTS moderators (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              tg_user_id INTEGER NOT NULL UNIQUE,
              created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE INDEX IF NOT EXISTS idx_moderators_user ON moderators(tg_user_id);

            CREATE TABLE IF NOT EXISTS users (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              tg_user_id INTEGER NOT NULL UNIQUE,
              lang TEXT NOT NULL DEFAULT 'ru',
              created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE INDEX IF NOT EXISTS idx_users_tg_id ON users(tg_user_id);

            CREATE TABLE IF NOT EXISTS documents (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              category TEXT NOT NULL,

              filename TEXT NOT NULL,
              storage_key TEXT NOT NULL,
              size_bytes INTEGER,
              mime TEXT NOT NULL,
              tg_file_id TEXT,
              uploaded_by INTEGER,
              uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE INDEX IF NOT EXISTS idx_documents_category ON documents(category);
            """
        )
        await self._conn.commit()


__all__ = ["Database"]
