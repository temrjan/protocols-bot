"""Free-text protocol search handlers.

This module contains handlers for the free-text search workflow:
- Search by protocol number or product name
- Text input processing
- Result display
"""

import re

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from bot.states import SearchState

router = Router(name="user_search")

# Text constants
TEXT = {
    "ru": {
        "ask_search_text": "Введите номер протокола или название препарата.",
        "search_no_results": "По вашему запросу ничего не найдено.",
    },
    "uz": {
        "ask_search_text": "Protokol raqamini yoki preparat nomini kiriting.",
        "search_no_results": "Sizning so'rovingiz bo'yicha ma'lumot topilmadi.",
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


@router.callback_query(F.data == "menu:search")
async def handle_search_menu(
    callback: CallbackQuery,
    state: FSMContext,
    user_repo,
) -> None:
    """Handle search menu callback - prompt for search text.
    
    Args:
        callback: Callback query.
        state: FSM state context.
        user_repo: User repository (injected by middleware).
    """
    user_id = callback.from_user.id
    lang = await user_repo.get_lang(user_id) or "ru"
    
    await state.set_state(SearchState.waiting_text)
    await callback.message.answer(get_text(lang, "ask_search_text"))
    await callback.answer()


@router.message(SearchState.waiting_text)
async def handle_search_text(
    message: Message,
    state: FSMContext,
    protocol_repo,
    user_repo,
) -> None:
    """Handle search text input - process search and show results.
    
    Args:
        message: Incoming message.
        state: FSM state context.
        protocol_repo: Protocol repository (injected by middleware).
        user_repo: User repository (injected by middleware).
    """
    from bot.keyboards import build_main_inline_keyboard
    from bot.utils.protocol import send_protocol_list
    
    user_id = message.from_user.id
    lang = await user_repo.get_lang(user_id) or "ru"
    
    raw_query = message.text or ""
    query = raw_query.strip()
    
    await state.clear()
    
    if not query:
        await message.answer(get_text(lang, "ask_search_text"))
        await message.answer(
            "Выберите действие:" if lang == "ru" else "Amalni tanlang:",
            reply_markup=build_main_inline_keyboard(lang),
        )
        return
    
    # Try to parse "YYYY <protocol>" format
    protocols = []
    year_match = re.match(r"^(\d{4})\s+(.+)$", query)
    if year_match:
        try:
            year_value = int(year_match.group(1))
        except ValueError:
            year_value = None
        protocol_fragment = year_match.group(2).strip()
        if year_value is not None and protocol_fragment:
            protocols = await protocol_repo.find_by_year_and_protocol(
                year_value, protocol_fragment
            )
    
    # If not found, try general code search
    if not protocols:
        protocols = await protocol_repo.find_by_code(query)
    
    # Send results
    if not protocols:
        await message.answer(get_text(lang, "search_no_results"))
    else:
        await send_protocol_list(message, protocols, lang)
    
    # Show main menu
    await message.answer(
        "Выберите действие:" if lang == "ru" else "Amalni tanlang:",
        reply_markup=build_main_inline_keyboard(lang),
    )


__all__ = ["router"]
