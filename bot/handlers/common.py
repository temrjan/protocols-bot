"""Common handlers for start, cancel, and language selection.

This module contains handlers for:
- /start command (language selection)
- /cancel command (cancel current operation)
- Language selection callbacks (lang:ru, lang:uz)
- Main menu navigation
"""

from aiogram import F, Router
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder

# Removed: from bot.keyboards import get_main_keyboard (using InlineKeyboard instead)

router = Router(name="common")

# Text constants for language selection
TEXT = {
    "ru": {
        "language_prompt": "Выберите язык / Tilni tanlang:",
        "cancelled": "Действие отменено.",
        "nothing_to_cancel": "Нет активного процесса.",
    },
    "uz": {
        "language_prompt": "Tilni tanlang:",
        "cancelled": "Amal bekor qilindi.",
        "nothing_to_cancel": "Faol jarayon yo'q.",
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


@router.message(CommandStart())
async def handle_start(
    message: Message,
    state: FSMContext,
    user_repo,
) -> None:
    """Handle /start command and show language selection.
    
    Args:
        message: Incoming message.
        state: FSM state context.
        user_repo: User repository (injected by middleware).
    """
    await state.clear()
    
    # Set default language
    user_id = message.from_user.id
    await user_repo.set_lang(user_id, "ru")
    await state.update_data(lang="ru")
    
    # Show language selection keyboard
    builder = InlineKeyboardBuilder()
    builder.button(text="🇷🇺 Русский", callback_data="lang:ru")
    builder.button(text="🇺🇿 O'zbekcha", callback_data="lang:uz")
    builder.adjust(1)
    
    await message.answer(
        TEXT["ru"]["language_prompt"],
        reply_markup=builder.as_markup(),
    )


@router.message(Command("cancel"))
async def handle_cancel(
    message: Message,
    state: FSMContext,
    user_repo,
) -> None:
    """Handle /cancel command to cancel current operation.
    
    Args:
        message: Incoming message.
        state: FSM state context.
        user_repo: User repository (injected by middleware).
    """
    user_id = message.from_user.id
    lang = await user_repo.get_lang(user_id) or "ru"
    
    current = await state.get_state()
    if current is None:
        await message.answer(get_text(lang, "nothing_to_cancel"))
        return
    
    await state.clear()
    await message.answer(get_text(lang, "cancelled"))

    # Show main menu with inline buttons
    builder = InlineKeyboardBuilder()
    if lang == "uz":
        builder.button(text="🔍 Filtr bo'yicha qidirish", callback_data="menu:filters")
        builder.button(text="🔎 Raqam bo'yicha qidirish", callback_data="menu:search")
        builder.button(text="📋 Qo'shimcha hujjatlar", callback_data="menu:documents")
    else:
        builder.button(text="🔍 Найти по фильтрам", callback_data="menu:filters")
        builder.button(text="🔎 Поиск по номеру", callback_data="menu:search")
        builder.button(text="📋 Дополнительные документы", callback_data="menu:documents")
    builder.adjust(1)

    await message.answer(
        "Выберите действие:" if lang == "ru" else "Amalni tanlang:",
        reply_markup=builder.as_markup(),
    )


@router.callback_query(F.data.startswith("lang:"))
async def handle_language(
    callback: CallbackQuery,
    state: FSMContext,
    user_repo,
) -> None:
    """Handle language selection callback.
    
    Args:
        callback: Callback query.
        state: FSM state context.
        user_repo: User repository (injected by middleware).
    """
    lang_code = callback.data.split(":", 1)[1]
    lang = lang_code if lang_code in TEXT else "ru"
    
    # Save language to database and state
    user_id = callback.from_user.id
    await user_repo.set_lang(user_id, lang)
    await state.update_data(lang=lang)
    
    # Remove inline keyboard
    try:
        await callback.message.edit_reply_markup()
    except Exception:
        pass
    
    await callback.answer()
    await state.clear()

    # Show main menu with inline buttons
    builder = InlineKeyboardBuilder()
    if lang == "uz":
        builder.button(text="🔍 Filtr bo'yicha qidirish", callback_data="menu:filters")
        builder.button(text="🔎 Raqam bo'yicha qidirish", callback_data="menu:search")
        builder.button(text="📋 Qo'shimcha hujjatlar", callback_data="menu:documents")
    else:
        builder.button(text="🔍 Найти по фильтрам", callback_data="menu:filters")
        builder.button(text="🔎 Поиск по номеру", callback_data="menu:search")
        builder.button(text="📋 Дополнительные документы", callback_data="menu:documents")
    builder.adjust(1)

    await callback.message.answer(
        "Выберите действие:" if lang == "ru" else "Amalni tanlang:",
        reply_markup=builder.as_markup(),
    )


__all__ = ["router"]
