"""Inline keyboard builders for the protocol bot.

This module provides functions to create inline keyboards (message-attached keyboards)
for interactive selections and actions.
"""

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder


def build_year_keyboard(years: list[int]) -> InlineKeyboardMarkup:
    """Build an inline keyboard for year selection.

    Args:
        years: List of available years.

    Returns:
        InlineKeyboardMarkup with year buttons (2 per row).
    """
    builder = InlineKeyboardBuilder()
    for year in years:
        builder.button(text=str(year), callback_data=f"year:{year}")
    builder.adjust(2)
    return builder.as_markup()


def build_product_keyboard(products: list[str]) -> InlineKeyboardMarkup:
    """Build an inline keyboard for product selection.

    Args:
        products: List of product names.

    Returns:
        InlineKeyboardMarkup with product buttons (1 per row, text trimmed to 32 chars).
    """
    builder = InlineKeyboardBuilder()
    for idx, product in enumerate(products):
        display_text = _shorten(product, limit=32)
        builder.button(text=display_text, callback_data=f"product:{idx}")
    builder.adjust(1)
    return builder.as_markup()


def build_download_keyboard(protocol_id: int, lang: str) -> InlineKeyboardMarkup:
    """Build an inline keyboard with a download button.

    Args:
        protocol_id: The database ID of the protocol.
        lang: Language code ('ru' or 'uz').

    Returns:
        InlineKeyboardMarkup with a download button.
    """
    text_map = {
        "ru": "📥 Скачать",
        "uz": "📥 Yuklab olish",
    }
    download_text = text_map.get(lang, text_map["ru"])

    keyboard = [
        [
            InlineKeyboardButton(
                text=download_text,
                callback_data=f"download:{protocol_id}",
            )
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def build_document_type_keyboard(lang: str) -> InlineKeyboardMarkup:
    """Build an inline keyboard for document type selection.

    Args:
        lang: Language code ('ru' or 'uz').

    Returns:
        InlineKeyboardMarkup with document type buttons.
    """
    text_map = {
        "ru": {
            "registration": "📄 Регистрационные документы",
            "declaration": "📋 Декларации соответствия",
        },
        "uz": {
            "registration": "📄 Ro'yxatdan o'tkazish hujjatlari",
            "declaration": "📋 Muvofiqlik deklaratsiyalari",
        },
    }
    texts = text_map.get(lang, text_map["ru"])

    keyboard = [
        [
            InlineKeyboardButton(
                text=texts["registration"],
                callback_data="doctype:registration",
            )
        ],
        [
            InlineKeyboardButton(
                text=texts["declaration"],
                callback_data="doctype:declaration",
            )
        ],
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def _shorten(text: str, limit: int = 32) -> str:
    """Shorten text to a specified limit.

    Args:
        text: The text to shorten.
        limit: Maximum length (default: 32).

    Returns:
        Shortened text with ellipsis if needed.
    """
    if len(text) <= limit:
        return text
    return text[: limit - 3] + "..."


__all__ = [
    "build_document_type_keyboard",
    "build_download_keyboard",
    "build_product_keyboard",
    "build_year_keyboard",
]
