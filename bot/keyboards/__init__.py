"""Keyboard builders for the protocol bot.

This package contains keyboard generation functions:
- reply: Reply keyboards (persistent menu at bottom of chat)
- inline: Inline keyboards (attached to messages)
"""

from bot.keyboards.inline import (
    MAIN_MENU_BUTTONS,
    build_document_type_keyboard,
    build_download_keyboard,
    build_main_inline_keyboard,
    build_product_keyboard,
    build_year_keyboard,
)
from bot.keyboards.reply import (
    get_admin_keyboard,
    get_cancel_keyboard,
    get_main_keyboard,
)

__all__ = [
    "MAIN_MENU_BUTTONS",
    # Inline keyboards
    "build_document_type_keyboard",
    "build_download_keyboard",
    "build_main_inline_keyboard",
    "build_product_keyboard",
    "build_year_keyboard",
    # Reply keyboards
    "get_admin_keyboard",
    "get_cancel_keyboard",
    "get_main_keyboard",
]
