"""Common handlers for start, cancel, and language selection.

This module contains handlers for:
- /start command (language selection)
- /cancel command (cancel current operation)
- Language selection callbacks (lang:ru, lang:uz)
- Main menu navigation
- Reply keyboard text fallback (for users with old reply keyboards)
"""

import contextlib

from aiogram import F, Router
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message, ReplyKeyboardRemove
from aiogram.utils.keyboard import InlineKeyboardBuilder

from bot.keyboards import MAIN_MENU_BUTTONS, build_main_inline_keyboard

router = Router(name="common")

# Collect all reply keyboard button texts for fallback matching
_REPLY_BUTTON_ACTIONS: dict[str, str] = {}
for _lang_texts in MAIN_MENU_BUTTONS.values():
    _REPLY_BUTTON_ACTIONS[_lang_texts["filters"]] = "menu:filters"
    _REPLY_BUTTON_ACTIONS[_lang_texts["search"]] = "menu:search"
    _REPLY_BUTTON_ACTIONS[_lang_texts["docs"]] = "menu:documents"

# Text constants for language selection
TEXT = {
    "ru": {
        "language_prompt": "Выберите язык / Tilni tanlang:",
        "choose_action": "Выберите действие:",
        "cancelled": "Действие отменено.",
        "nothing_to_cancel": "Нет активного процесса.",
    },
    "uz": {
        "language_prompt": "Tilni tanlang:",
        "choose_action": "Amalni tanlang:",
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

    # Preserve the user's saved language; default to ru only for new users.
    user_id = message.from_user.id
    saved_lang = await user_repo.get_lang(user_id)
    lang = saved_lang or "ru"
    if saved_lang is None:
        await user_repo.set_lang(user_id, lang)
    await state.update_data(lang=lang)

    # Remove any existing reply keyboard
    await message.answer(
        TEXT["ru"]["language_prompt"],
        reply_markup=ReplyKeyboardRemove(),
    )

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

    await message.answer(
        get_text(lang, "choose_action"),
        reply_markup=build_main_inline_keyboard(lang),
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
    with contextlib.suppress(Exception):
        await callback.message.edit_reply_markup()

    await callback.answer()
    await state.clear()

    await callback.message.answer(
        get_text(lang, "choose_action"),
        reply_markup=build_main_inline_keyboard(lang),
    )


@router.message(F.text.in_(_REPLY_BUTTON_ACTIONS.keys()))
async def handle_reply_keyboard_fallback(
    message: Message,
    state: FSMContext,
    user_repo,
    protocol_repo,
    document_repo,
) -> None:
    """Handle text from reply keyboard buttons.

    Users who still have the old reply keyboard will send plain text
    matching button labels. This handler catches those texts and
    triggers the corresponding inline menu action.

    Args:
        message: Incoming message with button text.
        state: FSM state context.
        user_repo: User repository (injected by middleware).
        protocol_repo: Protocol repository (injected by middleware).
        document_repo: Document repository (injected by middleware).
    """
    from bot.handlers.user.menus import (
        start_documents_flow,
        start_filters_flow,
        start_search_flow,
    )

    user_id = message.from_user.id
    lang = await user_repo.get_lang(user_id) or "ru"
    action = _REPLY_BUTTON_ACTIONS[message.text]

    # Remove the reply keyboard
    await message.answer(
        get_text(lang, "choose_action"),
        reply_markup=ReplyKeyboardRemove(),
    )

    await state.clear()

    if action == "menu:filters":
        await start_filters_flow(message, state, lang=lang, protocol_repo=protocol_repo)
    elif action == "menu:search":
        await start_search_flow(message, state, lang=lang)
    elif action == "menu:documents":
        await start_documents_flow(
            message, state, lang=lang, document_repo=document_repo
        )


__all__ = ["router"]
