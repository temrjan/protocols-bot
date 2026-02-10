"""Protocol repository for database operations."""

from typing import Any

import aiosqlite

from bot.database.models import Protocol
from bot.database.repositories.base import BaseRepository


class ProtocolRepository(BaseRepository[Protocol]):
    """Repository for Protocol database operations.

    Provides methods for CRUD operations on protocols table.
    """

    async def create(
        self,
        *,
        year: int,
        product: str,
        protocol_no: str,
        storage_key: str,
        filename: str,
        size_bytes: int | None,
        mime: str,
        uploaded_by: int | None,
        batch_no: str = "N/A",
        version: int = 1,
    ) -> int:
        """Create new protocol record.

        Args:
            year: Protocol year.
            product: Product name.
            protocol_no: Protocol number.
            storage_key: File storage key.
            filename: Original filename.
            size_bytes: File size in bytes.
            mime: MIME type.
            uploaded_by: Telegram user ID who uploaded.
            batch_no: Batch number (default: 'N/A').
            version: Protocol version (default: 1).

        Returns:
            ID of created protocol.
        """
        query = """
            INSERT INTO protocols
            (year, product, protocol_no, batch_no, version,
             storage_key, filename, size_bytes, mime, uploaded_by)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        cursor = await self.conn.execute(
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
        await self.conn.commit()
        return cursor.lastrowid

    async def deactivate_prev_versions(
        self,
        *,
        product: str,
        protocol_no: str,
        exclude_id: int | None = None,
    ) -> int:
        """Deactivate previous versions of protocol.

        Args:
            product: Product name.
            protocol_no: Protocol number.
            exclude_id: Protocol ID to exclude from deactivation.

        Returns:
            Number of deactivated protocols.
        """
        clauses = ["product = ?", "protocol_no = ?", "is_active = 1"]
        params: list[Any] = [product, protocol_no]
        if exclude_id is not None:
            clauses.append("id <> ?")
            params.append(exclude_id)
        query = "UPDATE protocols SET is_active = 0 WHERE " + " AND ".join(clauses)
        cursor = await self.conn.execute(query, tuple(params))
        await self.conn.commit()
        return cursor.rowcount

    async def set_tg_file_id(self, protocol_id: int, file_id: str) -> None:
        """Set Telegram file ID for protocol.

        Args:
            protocol_id: Protocol ID.
            file_id: Telegram file ID.
        """
        await self.conn.execute(
            "UPDATE protocols SET tg_file_id = ? WHERE id = ?",
            (file_id, protocol_id),
        )
        await self.conn.commit()

    async def find_by_filters(
        self,
        *,
        year: int | None = None,
        product: str | None = None,
        only_active: bool = True,
    ) -> list[Protocol]:
        """Find protocols by filters.

        Args:
            year: Protocol year filter.
            product: Product name filter (case-insensitive LIKE).
            only_active: Only return active protocols.

        Returns:
            List of protocols matching filters.
        """
        clauses = []
        params: list[Any] = []
        if year is not None:
            clauses.append("year = ?")
            params.append(year)
        if product:
            clauses.append("product LIKE ? COLLATE NOCASE")
            params.append(f"%{product}%")
        if only_active:
            clauses.append("is_active = 1")
        where = " WHERE " + " AND ".join(clauses) if clauses else ""
        query = (
            "SELECT * FROM protocols"
            + where
            + " ORDER BY year DESC, product COLLATE NOCASE ASC, uploaded_at DESC"
        )
        rows = await self._fetch_all(query, tuple(params))
        return [self._row_to_protocol(row) for row in rows]

    async def list_years(self, only_active: bool = True) -> list[int]:
        """List distinct years in protocols.

        Args:
            only_active: Only count active protocols.

        Returns:
            List of years in descending order.
        """
        clauses = []
        params: list[Any] = []
        if only_active:
            clauses.append("is_active = 1")
        where = " WHERE " + " AND ".join(clauses) if clauses else ""
        query = "SELECT DISTINCT year FROM protocols" + where + " ORDER BY year DESC"
        rows = await self._fetch_all(query, tuple(params))
        return [row["year"] for row in rows]

    async def list_products(self, year: int, only_active: bool = True) -> list[str]:
        """List distinct products for a year.

        Args:
            year: Protocol year.
            only_active: Only count active protocols.

        Returns:
            List of product names in alphabetical order.
        """
        clauses = ["year = ?"]
        params: list[Any] = [year]
        if only_active:
            clauses.append("is_active = 1")
        where = " WHERE " + " AND ".join(clauses)
        query = (
            "SELECT DISTINCT product FROM protocols"
            + where
            + " ORDER BY product COLLATE NOCASE ASC"
        )
        rows = await self._fetch_all(query, tuple(params))
        return [row["product"] for row in rows]

    async def find_by_code(self, code: str) -> list[Protocol]:
        """Find protocols by code (protocol_no or product).

        Args:
            code: Search code (case-insensitive LIKE).

        Returns:
            List of active protocols matching code.
        """
        pattern = f"%{code}%"
        query = """
            SELECT * FROM protocols
            WHERE (protocol_no LIKE ? COLLATE NOCASE OR product LIKE ? COLLATE NOCASE)
            AND is_active = 1
            ORDER BY uploaded_at DESC
        """
        rows = await self._fetch_all(query, (pattern, pattern))
        return [self._row_to_protocol(row) for row in rows]

    async def find_by_year_and_protocol(
        self, year: int, protocol_no: str
    ) -> list[Protocol]:
        """Find protocols by year and protocol number.

        Args:
            year: Protocol year.
            protocol_no: Protocol number (case-insensitive LIKE).

        Returns:
            List of active protocols matching filters.
        """
        pattern = f"%{protocol_no}%"
        query = """
            SELECT * FROM protocols
            WHERE year = ? AND protocol_no LIKE ? COLLATE NOCASE
            AND is_active = 1
            ORDER BY uploaded_at DESC
        """
        rows = await self._fetch_all(query, (year, pattern))
        return [self._row_to_protocol(row) for row in rows]

    async def get_by_id(self, protocol_id: int) -> Protocol | None:
        """Get protocol by ID.

        Args:
            protocol_id: Protocol ID.

        Returns:
            Protocol or None if not found.
        """
        query = "SELECT * FROM protocols WHERE id = ?"
        row = await self._fetch_one(query, (protocol_id,))
        return self._row_to_protocol(row) if row else None

    def _row_to_protocol(self, row: aiosqlite.Row) -> Protocol:
        """Convert database row to Protocol model.

        Args:
            row: Database row.

        Returns:
            Protocol model instance.
        """
        return Protocol(
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
