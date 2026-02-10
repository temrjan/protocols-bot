"""Common handlers for start, cancel, and language selection.

This module contains handlers for:
- /start command (language selection)
- /cancel command (cancel current operation)
- Language selection callbacks (lang:ru, lang:uz)
- Main menu navigation
- Reply keyboard text fallback (for users with old reply keyboards)
"""

from aiogram import F, Router
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message, ReplyKeyboardRemove
from aiogram.utils.keyboard import InlineKeyboardBuilder

from bot.keyboards import build_main_inline_keyboard, MAIN_MENU_BUTTONS

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

    # Set default language
    user_id = message.from_user.id
    await user_repo.set_lang(user_id, "ru")
    await state.update_data(lang="ru")

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
    try:
        await callback.message.edit_reply_markup()
    except Exception:
        pass

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
    from bot.keyboards import build_year_keyboard

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
        from bot.states import FilterStates

        years = await protocol_repo.list_years()
        if not years:
            await message.answer(
                "В базе пока нет доступных протоколов."
                if lang == "ru"
                else "Bazadda protokollar topilmadi.",
            )
            await message.answer(
                get_text(lang, "choose_action"),
                reply_markup=build_main_inline_keyboard(lang),
            )
            return
        await state.set_state(FilterStates.choosing_year)
        await message.answer(
            "Выберите год." if lang == "ru" else "Yilni tanlang.",
            reply_markup=build_year_keyboard(years),
        )

    elif action == "menu:search":
        from bot.states import SearchState

        await state.set_state(SearchState.waiting_text)
        await message.answer(
            "Введите номер протокола или название препарата."
            if lang == "ru"
            else "Protokol raqamini yoki preparat nomini kiriting.",
        )

    elif action == "menu:documents":
        from aiogram.utils.keyboard import InlineKeyboardBuilder

        categories = await document_repo.get_categories()
        if not categories:
            await message.answer(
                "Документы не найдены."
                if lang == "ru"
                else "Hujjatlar topilmadi.",
            )
            await message.answer(
                get_text(lang, "choose_action"),
                reply_markup=build_main_inline_keyboard(lang),
            )
            return
        builder = InlineKeyboardBuilder()
        for category in categories:
            builder.button(
                text=f"📁 {category}",
                callback_data=f"doc_category:{category}",
            )
        builder.adjust(1)
        await message.answer(
            "Выберите категорию документов:"
            if lang == "ru"
            else "Hujjat kategoriyasini tanlang:",
            reply_markup=builder.as_markup(),
        )


__all__ = ["router"]
