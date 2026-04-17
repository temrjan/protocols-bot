"""Protocol formatting and display utilities."""

import html

from aiogram.types import Message

from bot.database.models import Protocol
from bot.keyboards import build_download_keyboard

# Label translations
LABELS = {
    "ru": {
        "product": "Продукт",
        "protocol": "Протокол",
        "year": "Год",
        "uploaded": "Загружено",
        "filename": "Файл",
        "size": "Размер",
    },
    "uz": {
        "product": "Mahsulot",
        "protocol": "Protokol",
        "year": "Yil",
        "uploaded": "Yuklangan",
        "filename": "Fayl",
        "size": "Hajmi",
    },
}

# Text constants
TEXT = {
    "ru": {
        "no_protocols": "Протоколы не найдены.",
    },
    "uz": {
        "no_protocols": "Hech narsa topilmadi.",
    },
}


def get_labels(lang: str) -> dict[str, str]:
    """Get label translations for language.

    Args:
        lang: Language code ('ru' or 'uz').

    Returns:
        Dictionary of label translations.
    """
    return LABELS.get(lang, LABELS["ru"])


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


def format_size(value: int | None) -> str:
    """Format file size in human-readable format.

    Args:
        value: Size in bytes.

    Returns:
        Formatted size string.
    """
    if value is None:
        return "-"
    size = float(value)
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if size < 1024 or unit == "TB":
            if unit == "B":
                return f"{int(size)} B"
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{int(value)} B"


def format_protocol_text(protocol: Protocol, lang: str) -> str:
    """Format protocol information as text.

    Args:
        protocol: Protocol database model.
        lang: Language code ('ru' or 'uz').

    Returns:
        Formatted protocol information.
    """
    labels = get_labels(lang)
    uploaded_at = protocol.uploaded_at
    return (
        f"{labels['product']}: {html.escape(protocol.product)}\n"
        f"{labels['protocol']}: {html.escape(protocol.protocol_no)}\n"
        f"{labels['year']}: {protocol.year}\n"
        f"{labels['filename']}: {html.escape(protocol.filename)}\n"
        f"{labels['uploaded']}: {uploaded_at}"
    )


async def send_protocol_list(
    message: Message,
    protocols: list[Protocol],
    lang: str,
) -> None:
    """Send list of protocols to user.

    Args:
        message: Message to reply to.
        protocols: List of protocol models.
        lang: Language code ('ru' or 'uz').
    """
    from bot.utils import safe_send_many

    if not protocols:
        await message.answer(get_text(lang, "no_protocols"))
        return

    await safe_send_many(
        message,
        protocols,
        lambda protocol: (
            format_protocol_text(protocol, lang),
            build_download_keyboard(protocol.id, lang),
        ),
    )


__all__ = ["format_protocol_text", "format_size", "send_protocol_list"]
