"""Moderator management handlers for administrators.

This module contains handlers for moderator management:
- Add new moderator
- List moderators
- Admin menu navigation
"""

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder

from bot.states import AdminStates

router = Router(name="admin_moderators")

# Text constants
TEXT = {
    "ru": {
        "admin_menu_title": "Админ-панель. Выберите действие:",
        "admin_menu_upload": "Загрузить протокол",
        "admin_menu_upload_doc": "📋 Загрузить документ",
        "admin_menu_add_mod": "Назначить модератора",
        "admin_enter_moderator": "Введите Telegram ID пользователя, которому нужно выдать права загрузки.",
        "admin_invalid_id": "Введите корректный числовой Telegram ID.",
        "admin_moderator_added": "Пользователь {id} назначен модератором и теперь может загружать протоколы.",
        "admin_moderator_exists": "Этот пользователь уже имеет права для загрузки протоколов.",
        "admin_not_primary": "У вас нет доступа к админ-панели.",
    },
    "uz": {
        "admin_menu_title": "Admin panel. Amalni tanlang:",
        "admin_menu_upload": "Protokolni yuklash",
        "admin_menu_upload_doc": "📋 Hujjat yuklash",
        "admin_menu_add_mod": "Moderator tayinlash",
        "admin_enter_moderator": "Moderator qilish kerak bo'lgan foydalanuvchining Telegram ID raqamini kiriting.",
        "admin_invalid_id": "Iltimos, to'g'ri raqamli Telegram ID kiriting.",
        "admin_moderator_added": "{id} foydalanuvchi moderator etib tayinlandi va endi protokollarni yuklashi mumkin.",
        "admin_moderator_exists": "Bu foydalanuvchi allaqachon yuklash huquqiga ega.",
        "admin_not_primary": "Sizda admin panelga kirish huquqi yo'q.",
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


@router.message(Command("admin"))
async def handle_admin_menu(
    message: Message,
    state: FSMContext,
    user_repo,
) -> None:
    """Handle /admin command - show admin menu.

    Args:
        message: Incoming message.
        state: FSM state context.
        user_repo: User repository (injected by middleware).
    """
    from bot.core import settings

    user_id = message.from_user.id
    lang = await user_repo.get_lang(user_id) or "ru"

    # Check if user is primary admin
    if user_id != settings.PRIMARY_ADMIN_ID:
        await message.answer(get_text(lang, "admin_not_primary"))
        return

    await state.clear()

    # Build admin menu keyboard
    builder = InlineKeyboardBuilder()
    builder.button(text=get_text(lang, "admin_menu_upload"), callback_data="admin:upload")
    builder.button(text=get_text(lang, "admin_menu_upload_doc"), callback_data="admin:upload_doc")
    builder.button(text=get_text(lang, "admin_menu_add_mod"), callback_data="admin:add_mod")
    builder.adjust(1)

    await message.answer(
        get_text(lang, "admin_menu_title"),
        reply_markup=builder.as_markup(),
    )


@router.callback_query(F.data == "admin:add_mod")
async def handle_admin_add_moderator(
    callback: CallbackQuery,
    state: FSMContext,
    user_repo,
) -> None:
    """Handle add moderator callback - prompt for moderator ID.

    Args:
        callback: Callback query.
        state: FSM state context.
        user_repo: User repository (injected by middleware).
    """
    from bot.core import settings

    user_id = callback.from_user.id
    lang = await user_repo.get_lang(user_id) or "ru"

    # Check if user is primary admin
    if user_id != settings.PRIMARY_ADMIN_ID:
        await callback.answer(get_text(lang, "admin_not_primary"), show_alert=True)
        return

    await state.set_state(AdminStates.waiting_moderator_id)
    await callback.answer()
    await callback.message.answer(get_text(lang, "admin_enter_moderator"))


@router.message(AdminStates.waiting_moderator_id)
async def handle_admin_moderator_id(
    message: Message,
    state: FSMContext,
    moderator_repo,
    user_repo,
) -> None:
    """Handle moderator ID input - add moderator.

    Args:
        message: Incoming message.
        state: FSM state context.
        moderator_repo: Moderator repository (injected by middleware).
        user_repo: User repository (injected by middleware).
    """
    from bot.core import settings
    from bot.keyboards import get_main_keyboard

    user_id = message.from_user.id
    lang = await user_repo.get_lang(user_id) or "ru"

    # Check if user is primary admin
    if user_id != settings.PRIMARY_ADMIN_ID:
        await state.clear()
        await message.answer(get_text(lang, "admin_not_primary"))
        return

    raw_value = (message.text or "").strip()
    try:
        moderator_id = int(raw_value)
    except ValueError:
        await message.answer(get_text(lang, "admin_invalid_id"))
        return

    if moderator_id <= 0:
        await message.answer(get_text(lang, "admin_invalid_id"))
        return

    # Check if user is already a moderator
    is_already_moderator = await moderator_repo.is_moderator(moderator_id)
    if is_already_moderator:
        await message.answer(get_text(lang, "admin_moderator_exists"))
        await state.clear()
        await message.answer(
            "Выберите действие:" if lang == "ru" else "Amalni tanlang:",
            reply_markup=get_main_keyboard(lang),
        )
        return

    # Add moderator
    added = await moderator_repo.add_moderator(moderator_id)
    if added:
        await message.answer(get_text(lang, "admin_moderator_added").format(id=moderator_id))
    else:
        await message.answer(get_text(lang, "admin_moderator_exists"))

    await state.clear()
    await message.answer(
        "Выберите действие:" if lang == "ru" else "Amalni tanlang:",
        reply_markup=get_main_keyboard(lang),
    )


__all__ = ["router"]
