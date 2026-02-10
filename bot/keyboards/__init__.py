"""Keyboard builders for the protocol bot.

This package contains keyboard generation functions:
- reply: Reply keyboards (persistent menu at bottom of chat)
- inline: Inline keyboards (attached to messages)
"""

from bot.keyboards.inline import (
    build_document_type_keyboard,
    build_download_keyboard,
    build_product_keyboard,
    build_year_keyboard,
)
from bot.keyboards.reply import (
    get_admin_keyboard,
    get_cancel_keyboard,
    get_main_keyboard,
)

__all__ = [
    # Inline keyboards
    "build_document_type_keyboard",
    "build_download_keyboard",
    "build_product_keyboard",
    "build_year_keyboard",
    # Reply keyboards
    "get_admin_keyboard",
    "get_cancel_keyboard",
    "get_main_keyboard",
]
