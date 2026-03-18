"""Database models (dataclasses)."""

from dataclasses import dataclass


@dataclass
class Protocol:
    """Protocol record model.

    Attributes:
        id: Primary key.
        year: Protocol year.
        product: Product name.
        protocol_no: Protocol number.
        batch_no: Batch number.
        version: Protocol version (auto-incremented on re-upload).
        storage_key: File storage key.
        filename: Original filename.
        size_bytes: File size in bytes.
        mime: MIME type.
        tg_file_id: Telegram file ID (for faster re-sending).
        is_active: Active flag (only latest version is active).
        uploaded_by: Telegram user ID who uploaded.
        uploaded_at: Upload timestamp.
    """

    id: int
    year: int
    product: str
    protocol_no: str
    batch_no: str
    version: int
    storage_key: str
    filename: str
    size_bytes: int | None
    mime: str
    tg_file_id: str | None
    is_active: bool
    uploaded_by: int | None
    uploaded_at: str


@dataclass
class Moderator:
    """Moderator record model.

    Attributes:
        id: Primary key.
        tg_user_id: Telegram user ID.
        created_at: Creation timestamp.
    """

    id: int
    tg_user_id: int
    created_at: str


@dataclass
class User:
    """User record model.

    Attributes:
        id: Primary key.
        tg_user_id: Telegram user ID.
        lang: User language ('ru' or 'uz').
        created_at: Creation timestamp.
    """

    id: int
    tg_user_id: int
    lang: str
    created_at: str


@dataclass
class Document:
    """Additional document model (certificates, declarations, etc.).

    Attributes:
        id: Unique document identifier.
        category: Document category name (e.g., 'Регистрационные удостоверения').
        filename: File name.
        storage_key: Storage path key.
        size_bytes: File size in bytes.
        mime: MIME type.
        tg_file_id: Telegram file ID (cached for fast resend).
        uploaded_by: User ID who uploaded the document.
        uploaded_at: Upload timestamp.
    """

    id: int
    category: str
    filename: str
    storage_key: str
    size_bytes: int | None
    mime: str
    tg_file_id: str | None
    uploaded_by: int | None
    uploaded_at: str
