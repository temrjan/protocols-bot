"""Protocol business logic service."""

from pathlib import Path

from loguru import logger

from bot.database.repositories.protocol import ProtocolRepository
from bot.services.storage import StorageService
from bot.utils import protocol_storage_key


class ProtocolService:
    """Service for protocol operations.

    Provides high-level business logic for protocol management.
    """

    def __init__(
        self,
        repo: ProtocolRepository,
        storage: StorageService,
    ) -> None:
        """Initialize protocol service.

        Args:
            repo: Protocol repository instance.
            storage: Storage service instance.
        """
        self.repo = repo
        self.storage = storage

    async def upload_protocol(
        self,
        year: int,
        product: str,
        protocol_no: str,
        file_data: bytes,
        filename: str,
        mime: str,
        uploaded_by: int,
    ) -> int:
        """Upload new protocol with versioning.

        Deactivates old versions and saves new file.

        Args:
            year: Protocol year.
            product: Product name.
            protocol_no: Protocol number.
            file_data: File bytes.
            filename: Original filename.
            mime: MIME type.
            uploaded_by: Telegram user ID.

        Returns:
            Created protocol ID.

        Raises:
            Exception: If file save or database operation fails.
        """
        # Generate storage key
        ext = Path(filename).suffix or ".pdf"
        storage_key = protocol_storage_key(
            year=year,
            product=product,
            protocol_no=protocol_no,
            extension=ext,
        )

        logger.info(
            "Uploading protocol: year={}, product={}, protocol_no={}, size={}",
            year,
            product,
            protocol_no,
            len(file_data),
        )

        # Save file to storage
        await self.storage.save_bytes(storage_key, file_data, mime)

        # Deactivate old versions
        deactivated = await self.repo.deactivate_prev_versions(
            product=product,
            protocol_no=protocol_no,
        )
        if deactivated > 0:
            logger.info("Deactivated {} previous version(s)", deactivated)

        # Insert new protocol
        protocol_id = await self.repo.create(
            year=year,
            product=product,
            protocol_no=protocol_no,
            storage_key=storage_key,
            filename=filename,
            size_bytes=len(file_data),
            mime=mime,
            uploaded_by=uploaded_by,
        )

        logger.info("Created protocol with ID {}", protocol_id)
        return protocol_id
