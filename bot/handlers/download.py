"""Protocol download handlers.

This module contains handlers for protocol download:
- Download button callback
- File delivery with Telegram file ID caching
"""

import asyncio

from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import CallbackQuery, FSInputFile
from loguru import logger

router = Router(name="protocol_download")

# Text constants
TEXT = {
    "ru": {
        "no_protocols": "Протоколы не найдены.",
        "fetching": "Готовим файл…",
        "download_error": "Не удалось получить файл. Попробуйте позже.",
    },
    "uz": {
        "no_protocols": "Hech narsa topilmadi.",
        "fetching": "Fayl tayyorlanmoqda…",
        "download_error": "Faylni olishning imkoni bo'lmadi. Keyinroq qayta urinib ko'ring.",
    },
}


def get_text(lang: str, key: str) -> str:
    """Get localized text.

    Args:
        lang: Language code ('ru' or 'uz').
        key: Text key.

    Returns:
        Localized text string.
    """
    base = TEXT["ru"]
    data = TEXT.get(lang, base)
    return data.get(key, base.get(key, key))


async def fetch_from_local(protocol, storage_service) -> FSInputFile:
    """Fetch protocol file from local storage.

    Args:
        protocol: Protocol database model.
        storage_service: Storage service instance.

    Returns:
        FSInputFile ready to send.
    """
    from pathlib import Path

    path = await asyncio.to_thread(storage_service.get_path, protocol.storage_key)
    extension = Path(protocol.storage_key).suffix or ".pdf"
    filename = protocol.filename or f"{protocol.protocol_no}{extension}"
    return FSInputFile(path, filename=filename)


@router.callback_query(F.data.startswith("download:"))
async def handle_download(
    callback: CallbackQuery,
    protocol_repo,
    user_repo,
    storage_service,
) -> None:
    """Handle protocol download callback.

    Args:
        callback: Callback query.
        protocol_repo: Protocol repository (injected by middleware).
        user_repo: User repository (injected by middleware).
        storage_service: Storage service (injected by middleware).
    """
    from bot.utils.protocol import format_protocol_text

    user_id = callback.from_user.id
    lang = await user_repo.get_lang(user_id) or "ru"

    try:
        protocol_id = int(callback.data.split(":", 1)[1])
    except ValueError:
        await callback.answer("Invalid request", show_alert=True)
        return

    # Get protocol by ID
    protocol = await protocol_repo.get_by_id(protocol_id)
    if protocol is None:
        await callback.answer(get_text(lang, "no_protocols"), show_alert=True)
        return

    await callback.answer(get_text(lang, "fetching"))

    try:
        caption = format_protocol_text(protocol, lang)

        # Try to use cached Telegram file ID; on stale ID, invalidate and re-upload.
        if protocol.tg_file_id:
            try:
                if protocol.mime.startswith("image/"):
                    await callback.message.answer_photo(
                        protocol.tg_file_id, caption=caption
                    )
                else:
                    await callback.message.answer_document(
                        protocol.tg_file_id, caption=caption
                    )
                return
            except TelegramBadRequest as exc:
                logger.warning(
                    "Stale tg_file_id for protocol {id}: {err}; re-uploading",
                    id=protocol.id,
                    err=exc.message,
                )
                await protocol_repo.set_tg_file_id(protocol.id, None)

        # Fetch from local storage
        document = await fetch_from_local(protocol, storage_service)

        # Send file and cache Telegram file ID
        if protocol.mime.startswith("image/"):
            sent = await callback.message.answer_photo(document, caption=caption)
            file_id = sent.photo[-1].file_id if sent.photo else None
        else:
            sent = await callback.message.answer_document(document, caption=caption)
            file_id = sent.document.file_id if sent.document else None

        # Save Telegram file ID for future requests
        if file_id:
            await protocol_repo.set_tg_file_id(protocol.id, file_id)
        else:
            logger.warning(
                "Telegram did not return media info for protocol {protocol_id}",
                protocol_id=protocol.id,
            )

    except Exception:
        logger.exception("Failed to deliver protocol %s", protocol_id)
        await callback.message.answer(get_text(lang, "download_error"))


__all__ = ["router"]
