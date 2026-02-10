from __future__ import annotations

import aiosqlite
from aiosqlite import IntegrityError
from dataclasses import dataclass
from typing import Any, List, Optional

from loguru import logger


@dataclass
class ProtocolRecord:
    id: int
    year: int
    product: str
    protocol_no: str
    batch_no: str
    version: int
    storage_key: str
    filename: str
    size_bytes: Optional[int]
    mime: str
    tg_file_id: Optional[str]
    is_active: bool
    uploaded_by: Optional[int]
    uploaded_at: str


class Database:
    def __init__(self, path: str) -> None:
        self._path = path
        self._conn: Optional[aiosqlite.Connection] = None

    async def connect(self) -> None:
        if self._conn is None:
            self._conn = await aiosqlite.connect(self._path)
            self._conn.row_factory = aiosqlite.Row
            logger.debug("SQLite connection opened at {}", self._path)
            await self._ensure_schema()

    async def close(self) -> None:
        if self._conn is not None:
            await self._conn.close()
            self._conn = None
            logger.debug("SQLite connection closed")

    async def insert_protocol(
        self,
        *,
        year: int,
        product: str,
        protocol_no: str,
        storage_key: str,
        filename: str,
        size_bytes: Optional[int],
        mime: str,
        uploaded_by: Optional[int],
        batch_no: str = "N/A",
        version: int = 1,
    ) -> int:
        query = (
            "INSERT INTO protocols "
            "(year, product, protocol_no, batch_no, version, storage_key, filename, size_bytes, mime, uploaded_by) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"
        )
        conn = await self._require_conn()
        cursor = await conn.execute(
            query,
            (
                year,
                product,
                protocol_no,
                batch_no,
                version,
                storage_key,
                filename,
                size_bytes,
                mime,
                uploaded_by,
            ),
        )
        await conn.commit()
        return cursor.lastrowid

    async def deactivate_prev_versions(
        self,
        *,
        product: str,
        protocol_no: str,
        exclude_id: Optional[int] = None,
    ) -> int:
        clauses = ["product = ?", "protocol_no = ?", "is_active = 1"]
        params: List[Any] = [product, protocol_no]
        if exclude_id is not None:
            clauses.append("id <> ?")
            params.append(exclude_id)
        query = "UPDATE protocols SET is_active = 0 WHERE " + " AND ".join(clauses)
        conn = await self._require_conn()
        cursor = await conn.execute(query, tuple(params))
        await conn.commit()
        return cursor.rowcount

    async def set_tg_file_id(self, protocol_id: int, file_id: str) -> None:
        conn = await self._require_conn()
        await conn.execute("UPDATE protocols SET tg_file_id = ? WHERE id = ?", (file_id, protocol_id))
        await conn.commit()

    async def find_by_filters(
        self,
        *,
        year: Optional[int] = None,
        product: Optional[str] = None,
        only_active: bool = True,
    ) -> List[ProtocolRecord]:
        clauses = []
        params: List[Any] = []
        if year is not None:
            clauses.append("year = ?")
            params.append(year)
        if product:
            clauses.append("product LIKE ? COLLATE NOCASE")
            params.append(f"%{product}%")
        if only_active:
            clauses.append("is_active = 1")
        where = " WHERE " + " AND ".join(clauses) if clauses else ""
        query = "SELECT * FROM protocols" + where + " ORDER BY year DESC, product COLLATE NOCASE ASC, uploaded_at DESC"
        rows = await self._fetch_all(query, tuple(params))
        return [self._row_to_record(row) for row in rows]

    async def list_years(self, only_active: bool = True) -> List[int]:
        clauses = []
        params: List[Any] = []
        if only_active:
            clauses.append("is_active = 1")
        where = " WHERE " + " AND ".join(clauses) if clauses else ""
        query = "SELECT DISTINCT year FROM protocols" + where + " ORDER BY year DESC"
        rows = await self._fetch_all(query, tuple(params))
        return [row["year"] for row in rows]

    async def list_products(self, year: int, only_active: bool = True) -> List[str]:
        clauses = ["year = ?"]
        params: List[Any] = [year]
        if only_active:
            clauses.append("is_active = 1")
        where = " WHERE " + " AND ".join(clauses)
        query = "SELECT DISTINCT product FROM protocols" + where + " ORDER BY product COLLATE NOCASE ASC"
        rows = await self._fetch_all(query, tuple(params))
        return [row["product"] for row in rows]

    async def find_by_code(self, code: str) -> List[ProtocolRecord]:
        pattern = f"%{code}%"
        query = (
            "SELECT * FROM protocols WHERE (protocol_no LIKE ? COLLATE NOCASE OR product LIKE ? COLLATE NOCASE) "
            "AND is_active = 1 ORDER BY uploaded_at DESC"
        )
        rows = await self._fetch_all(query, (pattern, pattern))
        return [self._row_to_record(row) for row in rows]

    async def find_by_year_and_protocol(self, year: int, protocol_no: str) -> List[ProtocolRecord]:
        pattern = f"%{protocol_no}%"
        query = (
            "SELECT * FROM protocols WHERE year = ? AND protocol_no LIKE ? COLLATE NOCASE "
            "AND is_active = 1 ORDER BY uploaded_at DESC"
        )
        rows = await self._fetch_all(query, (year, pattern))
        return [self._row_to_record(row) for row in rows]

    async def get_by_id(self, protocol_id: int) -> Optional[ProtocolRecord]:
        query = "SELECT * FROM protocols WHERE id = ?"
        row = await self._fetch_one(query, (protocol_id,))
        return self._row_to_record(row) if row else None

    async def list_moderators(self) -> List[int]:
        rows = await self._fetch_all("SELECT tg_user_id FROM moderators ORDER BY tg_user_id", tuple())
        return [row["tg_user_id"] for row in rows]

    async def add_moderator(self, tg_user_id: int) -> bool:
        conn = await self._require_conn()
        try:
            await conn.execute(
                "INSERT INTO moderators (tg_user_id) VALUES (?)",
                (tg_user_id,),
            )
            await conn.commit()
            return True
        except IntegrityError:
            await conn.rollback()
            return False

    async def get_user_lang(self, tg_user_id: int) -> Optional[str]:
        row = await self._fetch_one(
            "SELECT lang FROM users WHERE tg_user_id = ?",
            (tg_user_id,),
        )
        return row["lang"] if row else None

    async def set_user_lang(self, tg_user_id: int, lang: str) -> None:
        conn = await self._require_conn()
        await conn.execute(
            "INSERT INTO users (tg_user_id, lang) VALUES (?, ?) "
            "ON CONFLICT(tg_user_id) DO UPDATE SET lang = excluded.lang",
            (tg_user_id, lang),
        )
        await conn.commit()

    async def _fetch_all(self, query: str, params: tuple[Any, ...]) -> List[aiosqlite.Row]:
        conn = await self._require_conn()
        cursor = await conn.execute(query, params)
        rows = await cursor.fetchall()
        await cursor.close()
        return rows

    async def _fetch_one(self, query: str, params: tuple[Any, ...]) -> Optional[aiosqlite.Row]:
        conn = await self._require_conn()
        cursor = await conn.execute(query, params)
        row = await cursor.fetchone()
        await cursor.close()
        return row

    async def _require_conn(self) -> aiosqlite.Connection:
        if self._conn is None:
            raise RuntimeError("Database connection not initialized")
        return self._conn

    async def _ensure_schema(self) -> None:
        conn = await self._require_conn()
        await conn.executescript(
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
            """
        )
        await conn.commit()

    def _row_to_record(self, row: aiosqlite.Row) -> ProtocolRecord:
        return ProtocolRecord(
            id=row["id"],
            year=row["year"],
            product=row["product"],
            protocol_no=row["protocol_no"],
            batch_no=row["batch_no"],
            version=row["version"],
            storage_key=row["storage_key"],
            filename=row["filename"],
            size_bytes=row["size_bytes"],
            mime=row["mime"],
            tg_file_id=row["tg_file_id"],
            is_active=bool(row["is_active"]),
            uploaded_by=row["uploaded_by"],
            uploaded_at=row["uploaded_at"],
        )


__all__ = ["Database", "ProtocolRecord"]
