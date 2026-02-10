from __future__ import annotations

import re
import unicodedata
from typing import Iterable

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
    product_slug = slugify(product)
    protocol_slug = slugify(protocol_no) or "protocol"
    ext = extension.lower()
    if not ext.startswith("."):
        ext = "." + ext
    return f"protocols/{year}/{product_slug}/{protocol_slug}{ext}"

def escape_markdown(text: str) -> str:
    return re.sub(r"([_*\\[\\]()~`>#+\-=|{}.!])", r"\\\1", text)

def chunk(iterable: Iterable, size: int):
    bucket = []
    for item in iterable:
        bucket.append(item)
        if len(bucket) == size:
            yield bucket
            bucket = []
    if bucket:
        yield bucket
