"""Reply keyboard builders for the protocol bot.

This module provides functions to create reply keyboards (persistent keyboards
at the bottom of the chat) for navigation and common actions.
"""

from aiogram.types import KeyboardButton, ReplyKeyboardMarkup


def get_main_keyboard(lang: str) -> ReplyKeyboardMarkup:
    """Build the main menu reply keyboard.

    Args:
        lang: Language code ('ru' or 'uz').

    Returns:
        ReplyKeyboardMarkup with main menu options.
    """
    text_map = {
        "ru": {
            "filters": "🔍 Найти по фильтрам",
            "search": "🔎 Поиск по номеру",
            "docs": "📋 Дополнительные документы",
        },
        "uz": {
            "filters": "🔍 Filtr bo'yicha qidirish",
            "search": "🔎 Raqam bo'yicha qidirish",
            "docs": "📋 Qo'shimcha hujjatlar",
        },
    }
    texts = text_map.get(lang, text_map["ru"])

    keyboard = [
        [KeyboardButton(text=texts["filters"])],
        [KeyboardButton(text=texts["search"])],
        [KeyboardButton(text=texts["docs"])],
    ]

    return ReplyKeyboardMarkup(
        keyboard=keyboard,
        resize_keyboard=True,
        one_time_keyboard=False,
    )


def get_cancel_keyboard(lang: str) -> ReplyKeyboardMarkup:
    """Build a keyboard with a cancel button.

    Args:
        lang: Language code ('ru' or 'uz').

    Returns:
        ReplyKeyboardMarkup with a cancel button.
    """
    text_map = {
        "ru": "❌ Отменить",
        "uz": "❌ Bekor qilish",
    }
    cancel_text = text_map.get(lang, text_map["ru"])

    keyboard = [[KeyboardButton(text=cancel_text)]]

    return ReplyKeyboardMarkup(
        keyboard=keyboard,
        resize_keyboard=True,
        one_time_keyboard=True,
    )


def get_admin_keyboard(lang: str) -> ReplyKeyboardMarkup:
    """Build the admin menu reply keyboard.

    Args:
        lang: Language code ('ru' or 'uz').

    Returns:
        ReplyKeyboardMarkup with admin menu options.
    """
    text_map = {
        "ru": {
            "upload": "📤 Загрузить протокол",
            "add_mod": "👤 Назначить модератора",
            "back": "◀️ Главное меню",
        },
        "uz": {
            "upload": "📤 Protokol yuklash",
            "add_mod": "👤 Moderator tayinlash",
            "back": "◀️ Asosiy menyu",
        },
    }
    texts = text_map.get(lang, text_map["ru"])

    keyboard = [
        [KeyboardButton(text=texts["upload"])],
        [KeyboardButton(text=texts["add_mod"])],
        [KeyboardButton(text=texts["back"])],
    ]

    return ReplyKeyboardMarkup(
        keyboard=keyboard,
        resize_keyboard=True,
        one_time_keyboard=False,
    )


__all__ = [
    "get_admin_keyboard",
    "get_cancel_keyboard",
    "get_main_keyboard",
]
