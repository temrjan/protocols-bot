"""Shared menu-entry flows.

The three user-facing sections (filters, search, additional documents) can
be triggered either by the inline main menu or by the legacy reply-keyboard
buttons. The handlers in those two paths used to duplicate the opening
logic; these helpers keep a single source of truth.

Each helper receives the ``Message`` to reply to and a ``FSMContext`` whose
previous state is the caller's responsibility to clear.
"""

from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from aiogram.utils.keyboard import InlineKeyboardBuilder

from bot.keyboards import build_main_inline_keyboard, build_year_keyboard
from bot.states import FilterStates, SearchState


def _choose_action_text(lang: str) -> str:
    """Return the 'choose action' prompt for the given language."""
    return "Выберите действие:" if lang == "ru" else "Amalni tanlang:"


async def start_filters_flow(
    message: Message,
    state: FSMContext,
    *,
    lang: str,
    protocol_repo,
) -> None:
    """Open the filter-based search flow (year → product → list)."""
    years = await protocol_repo.list_years()
    if not years:
        await message.answer(
            "В базе пока нет доступных протоколов."
            if lang == "ru"
            else "Bazadda protokollar topilmadi.",
        )
        await message.answer(
            _choose_action_text(lang),
            reply_markup=build_main_inline_keyboard(lang),
        )
        return

    await state.set_state(FilterStates.choosing_year)
    await message.answer(
        "Выберите год." if lang == "ru" else "Yilni tanlang.",
        reply_markup=build_year_keyboard(years),
    )


async def start_search_flow(
    message: Message,
    state: FSMContext,
    *,
    lang: str,
) -> None:
    """Open the free-text protocol search flow."""
    await state.set_state(SearchState.waiting_text)
    await message.answer(
        "Введите номер протокола или название препарата."
        if lang == "ru"
        else "Protokol raqamini yoki preparat nomini kiriting.",
    )


async def start_documents_flow(
    message: Message,
    state: FSMContext,
    *,
    lang: str,
    document_repo,
) -> None:
    """Open the additional documents flow (pick category → list files)."""
    await state.clear()
    categories = await document_repo.get_categories()
    if not categories:
        await message.answer(
            "Документы не найдены." if lang == "ru" else "Hujjatlar topilmadi.",
        )
        await message.answer(
            _choose_action_text(lang),
            reply_markup=build_main_inline_keyboard(lang),
        )
        return

    builder = InlineKeyboardBuilder()
    for idx, category in enumerate(categories):
        builder.button(text=f"📁 {category}", callback_data=f"doc_cat:{idx}")
    builder.adjust(1)

    await message.answer(
        "Выберите категорию документов:"
        if lang == "ru"
        else "Hujjat kategoriyasini tanlang:",
        reply_markup=builder.as_markup(),
    )


__all__ = ["start_documents_flow", "start_filters_flow", "start_search_flow"]
