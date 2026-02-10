"""Local file storage service."""

from pathlib import Path

import aiofiles
from loguru import logger


class StorageService:
    """Local file storage service.

    Provides asynchronous file storage operations with atomic writes.

    Attributes:
        root: Root storage directory.
    """

    def __init__(self, root: Path) -> None:
        """Initialize storage service.

        Args:
            root: Root storage directory path.
        """
        self.root = root
        # Ensure root directory exists
        self.root.mkdir(parents=True, exist_ok=True)

    async def save_bytes(self, key: str, data: bytes, mime: str) -> None:
        """Save file atomically.

        Uses temporary file and atomic rename to prevent partial writes.

        Args:
            key: Storage key (relative path).
            data: File data bytes.
            mime: MIME type (for logging/validation).

        Raises:
            ValueError: If storage key is invalid (contains .. or starts with /).
        """
        # Validate storage key
        if ".." in key or key.startswith("/"):
            raise ValueError(f"Invalid storage key: {key}")

        # Convert to safe path
        safe_key = key.replace("\\", "/")
        path = self.root / safe_key

        # Ensure path is within root
        normalized = path.resolve()
        if not str(normalized).startswith(str(self.root.resolve())):
            raise ValueError(f"Storage key escapes root directory: {key}")

        # Create parent directories
        path.parent.mkdir(parents=True, exist_ok=True)

        # Atomic write using temporary file
        tmp_path = path.with_suffix(path.suffix + ".tmp")
        try:
            async with aiofiles.open(tmp_path, "wb") as f:
                await f.write(data)

            # Atomic rename
            tmp_path.replace(path)
            logger.info("Stored file at {} ({} bytes)", path, len(data))
        except Exception as e:
            # Clean up temporary file on error
            if tmp_path.exists():
                tmp_path.unlink()
            logger.error("Failed to store file at {}: {}", path, str(e))
            raise

    def get_path(self, key: str) -> Path:
        """Get file path by storage key.

        Args:
            key: Storage key.

        Returns:
            Absolute file path.

        Raises:
            ValueError: If storage key is invalid.
        """
        # Validate storage key
        if ".." in key or key.startswith("/"):
            raise ValueError(f"Invalid storage key: {key}")

        # Convert to safe path
        safe_key = key.replace("\\", "/")
        path = self.root / safe_key

        # Ensure path is within root
        normalized = path.resolve()
        if not str(normalized).startswith(str(self.root.resolve())):
            raise ValueError(f"Storage key escapes root directory: {key}")

        return path

    def exists(self, key: str) -> bool:
        """Check if file exists.

        Args:
            key: Storage key.

        Returns:
            True if file exists.
        """
        try:
            path = self.get_path(key)
            return path.exists()
        except ValueError:
            return False

    def get_size(self, key: str) -> int | None:
        """Get file size in bytes.

        Args:
            key: Storage key.

        Returns:
            File size in bytes or None if file doesn't exist.
        """
        try:
            path = self.get_path(key)
            if path.exists():
                return path.stat().st_size
            return None
        except (ValueError, OSError):
            return None
