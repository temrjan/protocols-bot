"""Document repository for database operations."""

import aiosqlite

from bot.database.models import Document
from bot.database.repositories.base import BaseRepository


class DocumentRepository(BaseRepository[Document]):
    """Repository for Document database operations.

    Provides methods for managing additional documents (certificates, declarations, etc.).
    """

    async def get_categories(self) -> list[str]:
        """Get all unique document categories.

        Returns:
            List of category names sorted alphabetically.
        """
        query = """
            SELECT DISTINCT category FROM documents
            ORDER BY category COLLATE NOCASE ASC
        """
        rows = await self._fetch_all(query)
        return [row["category"] for row in rows]

    async def find_by_category(self, category: str) -> list[Document]:
        """Find documents by category.

        Args:
            category: Document category name.

        Returns:
            List of documents in the category.
        """
        query = """
            SELECT * FROM documents
            WHERE category = ?
            ORDER BY uploaded_at DESC
        """
        rows = await self._fetch_all(query, (category,))
        return [self._row_to_document(row) for row in rows]

    async def get_by_id(self, doc_id: int) -> Document | None:
        """Get document by ID.

        Args:
            doc_id: Document ID.

        Returns:
            Document or None if not found.
        """
        query = "SELECT * FROM documents WHERE id = ?"
        row = await self._fetch_one(query, (doc_id,))
        return self._row_to_document(row) if row else None

    async def update_file_id(self, doc_id: int, file_id: str) -> None:
        """Update Telegram file ID for document.

        Args:
            doc_id: Document ID.
            file_id: Telegram file ID.
        """
        await self.conn.execute(
            "UPDATE documents SET tg_file_id = ? WHERE id = ?",
            (file_id, doc_id),
        )
        await self.conn.commit()

    def _row_to_document(self, row: aiosqlite.Row) -> Document:
        """Convert database row to Document model.

        Args:
            row: Database row.

        Returns:
            Document model instance.
        """
        return Document(
            id=row["id"],
            category=row["category"],
            filename=row["filename"],
            storage_key=row["storage_key"],
            size_bytes=row["size_bytes"],
            mime=row["mime"],
            tg_file_id=row["tg_file_id"],
            uploaded_by=row["uploaded_by"],
            uploaded_at=row["uploaded_at"],
        )


__all__ = ["DocumentRepository"]
