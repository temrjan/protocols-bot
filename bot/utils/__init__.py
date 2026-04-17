"""Utility functions for the bot."""

import asyncio
import re
import unicodedata
from collections.abc import Callable, Iterable
from typing import TYPE_CHECKING, TypeVar

if TYPE_CHECKING:
    from aiogram.types import InlineKeyboardMarkup, Message

TRANSLIT_MAP = {
    "а": "a",
    "б": "b",
    "в": "v",
    "г": "g",
    "д": "d",
    "е": "e",
    "ё": "e",
    "ж": "zh",
    "з": "z",
    "и": "i",
    "й": "y",
    "к": "k",
    "л": "l",
    "м": "m",
    "н": "n",
    "о": "o",
    "п": "p",
    "р": "r",
    "с": "s",
    "т": "t",
    "у": "u",
    "ф": "f",
    "х": "h",
    "ц": "ts",
    "ч": "ch",
    "ш": "sh",
    "щ": "sch",
    "ъ": "",
    "ы": "y",
    "ь": "",
    "э": "e",
    "ю": "yu",
    "я": "ya",
}


def slugify(text: str) -> str:
    """Convert text to URL-friendly slug.

    Args:
        text: Text to slugify.

    Returns:
        Slugified text.
    """
    normalized = unicodedata.normalize("NFKD", text).lower()
    transliterated = "".join(TRANSLIT_MAP.get(ch, ch) for ch in normalized)
    cleaned = re.sub(r"[^a-z0-9]+", "-", transliterated)
    return cleaned.strip("-")


def protocol_storage_key(
    *,
    year: int,
    product: str,
    protocol_no: str,
    extension: str = ".pdf",
) -> str:
    """Generate storage key for protocol file.

    Args:
        year: Protocol year.
        product: Product name.
        protocol_no: Protocol number.
        extension: File extension (default: .pdf).

    Returns:
        Storage key path.
    """
    product_slug = slugify(product)
    protocol_slug = slugify(protocol_no) or "protocol"
    ext = extension.lower()
    if not ext.startswith("."):
        ext = "." + ext
    return f"protocols/{year}/{product_slug}/{protocol_slug}{ext}"


def escape_markdown(text: str) -> str:
    """Escape markdown special characters.

    Args:
        text: Text to escape.

    Returns:
        Escaped text.
    """
    return re.sub(r"([_*\\[\\]()~`>#+\-=|{}.!])", r"\\\1", text)


def chunk(iterable: Iterable, size: int):
    """Split iterable into chunks of specified size.

    Args:
        iterable: Iterable to chunk.
        size: Chunk size.

    Yields:
        Chunks of specified size.
    """
    bucket = []
    for item in iterable:
        bucket.append(item)
        if len(bucket) == size:
            yield bucket
            bucket = []
    if bucket:
        yield bucket


T = TypeVar("T")


async def safe_send_many(
    message: "Message",
    items: Iterable[T],
    builder: Callable[[T], "tuple[str, InlineKeyboardMarkup | None]"],
    *,
    pause: float = 0.05,
) -> None:
    """Send one message per item while respecting Telegram's flood limits.

    Paces individual ``message.answer`` calls with a short ``pause`` between
    them and handles ``TelegramRetryAfter`` by sleeping for the requested
    interval and retrying the failed message exactly once. Longer-running
    bursts (category listings, search results) stay well under the ~30
    messages/sec per-chat cap.

    Args:
        message: The aiogram message used to reply.
        items: Iterable of records to render.
        builder: Function that maps a record to ``(text, reply_markup)``.
        pause: Seconds to wait between sends.
    """
    from aiogram.exceptions import TelegramRetryAfter

    first = True
    for item in items:
        if not first:
            await asyncio.sleep(pause)
        first = False

        text, reply_markup = builder(item)
        try:
            await message.answer(text, reply_markup=reply_markup)
        except TelegramRetryAfter as exc:
            await asyncio.sleep(exc.retry_after)
            await message.answer(text, reply_markup=reply_markup)


__all__ = [
    "chunk",
    "escape_markdown",
    "protocol_storage_key",
    "safe_send_many",
    "slugify",
]

# Localization
from bot.utils.text import TEXT, get_text

__all__.extend(["TEXT", "get_text"])

# Protocol utilities
from bot.utils.protocol import format_size

__all__.append("format_size")
