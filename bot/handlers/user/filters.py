"""Filter-based protocol search handlers.

This module contains handlers for the filter-based protocol search workflow:
- Year selection
- Product selection
- Protocol list display
"""

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery

from bot.core.products import get_predefined_products
from bot.keyboards import build_product_keyboard, build_year_keyboard
from bot.states import FilterStates

router = Router(name="user_filters")

# Text constants
TEXT = {
    "ru": {
        "choose_year": "Выберите год.",
        "choose_product": "Выберите препарат.",
        "no_years": "В базе пока нет доступных протоколов.",
        "no_products": "Для выбранного года протоколы не найдены.",
        "no_protocols": "Протоколы не найдены.",
    },
    "uz": {
        "choose_year": "Yilni tanlang.",
        "choose_product": "Preparatni tanlang.",
        "no_years": "Bazadda protokollar topilmadi.",
        "no_products": "Tanlangan yil uchun protokollar yo'q.",
        "no_protocols": "Hech narsa topilmadi.",
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


@router.callback_query(F.data == "menu:filters")
async def handle_filters_menu(
    callback: CallbackQuery,
    state: FSMContext,
    protocol_repo,
    user_repo,
) -> None:
    """Handle filter menu callback - show year selection.

    Args:
        callback: Callback query.
        state: FSM state context.
        protocol_repo: Protocol repository (injected by middleware).
        user_repo: User repository (injected by middleware).
    """
    from bot.handlers.user.menus import start_filters_flow

    user_id = callback.from_user.id
    lang = await user_repo.get_lang(user_id) or "ru"

    await callback.answer()
    await state.clear()
    await start_filters_flow(
        callback.message, state, lang=lang, protocol_repo=protocol_repo
    )


@router.callback_query(F.data.startswith("year:"))
async def handle_year_selection(
    callback: CallbackQuery,
    state: FSMContext,
    protocol_repo,
    user_repo,
) -> None:
    """Handle year selection callback - show product selection.

    No FSM state filter: the year is parsed from callback data,
    so this handler works even after bot restart (MemoryStorage lost).

    Args:
        callback: Callback query.
        state: FSM state context.
        protocol_repo: Protocol repository (injected by middleware).
        user_repo: User repository (injected by middleware).
    """
    user_id = callback.from_user.id
    lang = await user_repo.get_lang(user_id) or "ru"

    try:
        year = int(callback.data.split(":", 1)[1])
    except ValueError:
        await callback.answer("Invalid year", show_alert=True)
        return

    # Get products for year (use predefined list or fetch from DB)
    products = get_predefined_products()
    if not products:
        products = await protocol_repo.list_products(year)

    if not products:
        await callback.answer(get_text(lang, "no_products"), show_alert=True)
        return

    # Store selected year and products in state
    await state.update_data(selected_year=year, products=products)
    await state.set_state(FilterStates.choosing_product)

    # Show product selection keyboard
    await callback.message.answer(
        get_text(lang, "choose_product"),
        reply_markup=build_product_keyboard(products),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("product:"))
async def handle_product_selection(
    callback: CallbackQuery,
    state: FSMContext,
    protocol_repo,
    user_repo,
) -> None:
    """Handle product selection callback - show protocol list.

    No FSM state filter: works even if state was lost (bot restart).
    Falls back to year selection when state data is missing.

    Args:
        callback: Callback query.
        state: FSM state context.
        protocol_repo: Protocol repository (injected by middleware).
        user_repo: User repository (injected by middleware).
    """
    from bot.keyboards import build_main_inline_keyboard
    from bot.utils.protocol import send_protocol_list

    user_id = callback.from_user.id
    lang = await user_repo.get_lang(user_id) or "ru"

    # Get state data
    data = await state.get_data()
    products = data.get("products", [])

    try:
        index = int(callback.data.split(":", 1)[1])
    except ValueError:
        await callback.answer("Invalid product", show_alert=True)
        return

    # State lost (bot restart / stale keyboard) — restart filter flow
    if not products or index < 0 or index >= len(products):
        await state.clear()
        years = await protocol_repo.list_years()
        if not years:
            await callback.answer(get_text(lang, "no_years"), show_alert=True)
            return
        await state.set_state(FilterStates.choosing_year)
        await callback.message.answer(
            get_text(lang, "choose_year"),
            reply_markup=build_year_keyboard(years),
        )
        await callback.answer()
        return

    product = products[index]
    year = data.get("selected_year")

    await state.clear()

    # Find protocols by filters
    protocols = await protocol_repo.find_by_filters(year=year, product=product)

    # Send protocol list
    await send_protocol_list(callback.message, protocols, lang)

    # Show main menu
    await callback.message.answer(
        "Выберите действие:" if lang == "ru" else "Amalni tanlang:",
        reply_markup=build_main_inline_keyboard(lang),
    )
    await callback.answer()


__all__ = ["router"]
