"""Protocol upload handlers for administrators.

This module contains handlers for protocol file upload workflow:
- File reception (document/photo)
- Year selection
- Product selection
- Protocol number input
- File processing and storage
"""

import asyncio
import io
from datetime import datetime
from pathlib import Path

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, FSInputFile, InlineKeyboardMarkup, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder
from loguru import logger

from bot.states import UploadStates

router = Router(name="admin_upload")

# Allowed file types
ALLOWED_MIME_TYPES = {
    "application/pdf": (".pdf",),
    "image/jpeg": (".jpg", ".jpeg"),
    "image/jpg": (".jpg", ".jpeg"),
}

EXTENSION_TO_MIME = {
    ".pdf": "application/pdf",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
}

# Product names
PRODUCT_NAMES = (
    "DERMACOMPLEX",
    "OPHTALMOCOMPLEX",
    "NEUROCOMPLEX KIDS",
    "IMMUNOCOMPLEX",
    "IMMUNOCOMPLEX KIDS",
    "CALCIY TRIACTIVE D3",
    "BIFOLAK ZINCUM+C+D3",
    "BIFOLAK ZINCUM",
    "BIFOLAK MAGNIY / CAPSULA",
    "BIFOLAK MAGNIY / STICK",
    "BIFOLAK ACTIVE / CAPSULA",
    "BIFOLAK ACTIVE / STICK",
    "BIFOLAK NEO",
)

# Text constants
TEXT = {
    "ru": {
        "not_admin": "У вас нет прав для загрузки протоколов.",
        "admin_start": "Загрузка протокола. Укажите год (например, 2025) или выберите кнопку ниже.",
        "admin_invalid_year": "Введите год числом, например 2025.",
        "admin_choose_product": "Выберите название препарата из списка.",
        "admin_ask_product": "Введите название препарата.",
        "admin_ask_protocol_no": "Введите номер протокола.",
        "admin_invalid_file": "Принимаются только PDF или JPG-файлы до 50 МБ.",
        "admin_file_too_large": "Файл слишком большой (максимум 50 МБ).",
        "admin_success": "Протокол загружен и сохранён.",
        "admin_error": "Не удалось загрузить протокол. Попробуйте позже.",
        "admin_upload_hint": "Чтобы загрузить протокол, отправьте PDF или JPG-файл в чат.",
    },
    "uz": {
        "not_admin": "Sizga protokollarni yuklashga ruxsat berilmagan.",
        "admin_start": "Protokol yuklash. Yilni kiriting (masalan, 2025) yoki pastdagi tugmani tanlang.",
        "admin_invalid_year": "Iltimos, yilni raqam bilan kiriting (masalan, 2025).",
        "admin_choose_product": "Preparat nomini ro'yxatdan tanlang.",
        "admin_ask_product": "Preparat nomini kiriting.",
        "admin_ask_protocol_no": "Protokol raqamini kiriting.",
        "admin_invalid_file": "Faqat 50 MB gacha bo'lgan PDF yoki JPG fayllar qabul qilinadi.",
        "admin_file_too_large": "Fayl juda katta (maksimal 50 MB).",
        "admin_success": "Protokol yuklandi va saqlandi.",
        "admin_error": "Protokolni yuklab bo'lmadi. Keyinroq urinib ko'ring.",
        "admin_upload_hint": "Protokolni yuklash uchun PDF yoki JPG faylini shu chatga yuboring.",
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


def get_predefined_products() -> list[str]:
    """Get list of predefined product names.

    Returns:
        List of product name strings.
    """
    return [item.strip() for item in PRODUCT_NAMES if item.strip()]


def build_product_keyboard(products: list[str]) -> InlineKeyboardMarkup:
    """Build product selection keyboard.

    Args:
        products: List of product names.

    Returns:
        InlineKeyboardMarkup with product buttons.
    """
    builder = InlineKeyboardBuilder()
    for idx, product in enumerate(products):
        display_text = product[:29] + "..." if len(product) > 32 else product
        builder.button(text=display_text, callback_data=f"upload_product:{idx}")
    builder.adjust(1)
    return builder.as_markup()


def build_year_keyboard() -> InlineKeyboardMarkup:
    """Build year selection keyboard.

    Returns:
        InlineKeyboardMarkup with current and previous year buttons.
    """
    builder = InlineKeyboardBuilder()
    current_year = datetime.now().year
    builder.button(text=str(current_year), callback_data=f"upload_year:{current_year}")
    previous_year = current_year - 1
    builder.button(text=str(previous_year), callback_data=f"upload_year:{previous_year}")
    builder.adjust(2)
    return builder.as_markup()


async def proceed_after_year(
    message: Message,
    state: FSMContext,
    lang: str,
    year: int,
) -> None:
    """Proceed to product selection after year is chosen.

    Args:
        message: Message to reply to.
        state: FSM state context.
        lang: Language code.
        year: Selected year.
    """
    await state.update_data(year=year)
    products = get_predefined_products()

    if products:
        await state.update_data(products=products)
        await state.set_state(UploadStates.choosing_product)
        await message.answer(
            get_text(lang, "admin_choose_product"),
            reply_markup=build_product_keyboard(products),
        )
    else:
        await state.update_data(products=[])
        await state.set_state(UploadStates.waiting_product)
        await message.answer(get_text(lang, "admin_ask_product"))


@router.callback_query(F.data == "admin:upload")
async def handle_admin_upload_menu(
    callback: CallbackQuery,
    state: FSMContext,
    user_repo,
) -> None:
    """Handle admin upload menu callback.

    Args:
        callback: Callback query.
        state: FSM state context.
        user_repo: User repository (injected by middleware).
    """
    user_id = callback.from_user.id
    lang = await user_repo.get_lang(user_id) or "ru"

    await state.clear()
    await callback.answer()
    await callback.message.answer(get_text(lang, "admin_upload_hint"))


@router.message(F.document)
async def handle_document(
    message: Message,
    state: FSMContext,
    moderator_repo,
    user_repo,
) -> None:
    """Handle document upload - prepare for protocol upload.

    Args:
        message: Incoming message with document.
        state: FSM state context.
        moderator_repo: Moderator repository (injected by middleware).
        user_repo: User repository (injected by middleware).
    """
    user_id = message.from_user.id
    lang = await user_repo.get_lang(user_id) or "ru"

    # Check if user has upload rights
    is_moderator = await moderator_repo.is_moderator(user_id)
    if not is_moderator:
        await message.answer(get_text(lang, "not_admin"))
        return

    document = message.document
    if document is None:
        await message.answer(get_text(lang, "not_admin"))
        return

    mime = (document.mime_type or "").lower()
    filename = document.file_name or ""

    if not filename:
        default_ext = ".pdf"
        if mime in ALLOWED_MIME_TYPES:
            default_ext = ALLOWED_MIME_TYPES[mime][0]
        filename = f"protocol{default_ext}"

    await state.clear()
    await state.update_data(
        file_id=document.file_id,
        filename=filename,
        mime=mime or "",
        file_size=document.file_size,
        uploader=user_id,
    )
    await state.set_state(UploadStates.waiting_year)
    await message.answer(
        get_text(lang, "admin_start"),
        reply_markup=build_year_keyboard(),
    )


@router.message(F.photo)
async def handle_photo(
    message: Message,
    state: FSMContext,
    moderator_repo,
    user_repo,
) -> None:
    """Handle photo upload - prepare for protocol upload.

    Args:
        message: Incoming message with photo.
        state: FSM state context.
        moderator_repo: Moderator repository (injected by middleware).
        user_repo: User repository (injected by middleware).
    """
    user_id = message.from_user.id
    lang = await user_repo.get_lang(user_id) or "ru"

    # Check if user has upload rights
    is_moderator = await moderator_repo.is_moderator(user_id)
    if not is_moderator:
        await message.answer(get_text(lang, "not_admin"))
        return

    if not message.photo:
        await message.answer(get_text(lang, "admin_invalid_file"))
        return

    photo = message.photo[-1]
    filename = f"protocol-{photo.file_unique_id}.jpg"

    await state.clear()
    await state.update_data(
        file_id=photo.file_id,
        filename=filename,
        mime="image/jpeg",
        file_size=photo.file_size,
        uploader=user_id,
    )
    await state.set_state(UploadStates.waiting_year)
    await message.answer(
        get_text(lang, "admin_start"),
        reply_markup=build_year_keyboard(),
    )


@router.message(UploadStates.waiting_year)
async def handle_upload_year_text(
    message: Message,
    state: FSMContext,
    moderator_repo,
    user_repo,
) -> None:
    """Handle year text input.

    Args:
        message: Incoming message.
        state: FSM state context.
        moderator_repo: Moderator repository (injected by middleware).
        user_repo: User repository (injected by middleware).
    """
    user_id = message.from_user.id
    lang = await user_repo.get_lang(user_id) or "ru"

    is_moderator = await moderator_repo.is_moderator(user_id)
    if not is_moderator:
        await state.clear()
        await message.answer(get_text(lang, "not_admin"))
        return

    text = (message.text or "").strip()
    try:
        year = int(text)
    except ValueError:
        await message.answer(get_text(lang, "admin_invalid_year"))
        return

    await proceed_after_year(message, state, lang, year)


@router.callback_query(UploadStates.waiting_year, F.data.startswith("upload_year:"))
async def handle_upload_year_callback(
    callback: CallbackQuery,
    state: FSMContext,
    moderator_repo,
    user_repo,
) -> None:
    """Handle year selection callback.

    Args:
        callback: Callback query.
        state: FSM state context.
        moderator_repo: Moderator repository (injected by middleware).
        user_repo: User repository (injected by middleware).
    """
    user_id = callback.from_user.id
    lang = await user_repo.get_lang(user_id) or "ru"

    is_moderator = await moderator_repo.is_moderator(user_id)
    if not is_moderator:
        await state.clear()
        await callback.answer(get_text(lang, "not_admin"), show_alert=True)
        return

    try:
        year = int(callback.data.split(":", 1)[1])
    except ValueError:
        await callback.answer("Invalid year", show_alert=True)
        return

    try:
        await callback.message.edit_reply_markup()
    except Exception:
        pass

    await callback.answer()
    await proceed_after_year(callback.message, state, lang, year)


@router.message(UploadStates.choosing_product)
async def handle_upload_product_prompt(
    message: Message,
    state: FSMContext,
    moderator_repo,
    user_repo,
) -> None:
    """Handle product prompt during choosing_product state.

    Args:
        message: Incoming message.
        state: FSM state context.
        moderator_repo: Moderator repository (injected by middleware).
        user_repo: User repository (injected by middleware).
    """
    user_id = message.from_user.id
    lang = await user_repo.get_lang(user_id) or "ru"

    is_moderator = await moderator_repo.is_moderator(user_id)
    if not is_moderator:
        await state.clear()
        await message.answer(get_text(lang, "not_admin"))
        return

    data = await state.get_data()
    products = data.get("products", [])

    if not products:
        await state.set_state(UploadStates.waiting_product)
        await message.answer(get_text(lang, "admin_ask_product"))
        return

    await message.answer(
        get_text(lang, "admin_choose_product"),
        reply_markup=build_product_keyboard(products),
    )


@router.callback_query(UploadStates.choosing_product, F.data.startswith("upload_product:"))
async def handle_upload_product_callback(
    callback: CallbackQuery,
    state: FSMContext,
    moderator_repo,
    user_repo,
) -> None:
    """Handle product selection callback.

    Args:
        callback: Callback query.
        state: FSM state context.
        moderator_repo: Moderator repository (injected by middleware).
        user_repo: User repository (injected by middleware).
    """
    user_id = callback.from_user.id
    lang = await user_repo.get_lang(user_id) or "ru"

    is_moderator = await moderator_repo.is_moderator(user_id)
    if not is_moderator:
        await state.clear()
        await callback.answer(get_text(lang, "not_admin"), show_alert=True)
        return

    data = await state.get_data()
    products = data.get("products", [])

    try:
        index = int(callback.data.split(":", 1)[1])
    except ValueError:
        await callback.answer("Invalid product", show_alert=True)
        return

    if index < 0 or index >= len(products):
        await callback.answer("Unavailable", show_alert=True)
        return

    product = products[index]
    await state.update_data(product=product)
    await state.set_state(UploadStates.waiting_protocol_no)

    try:
        await callback.message.edit_reply_markup()
    except Exception:
        pass

    await callback.answer()
    await callback.message.answer(get_text(lang, "admin_ask_protocol_no"))


@router.message(UploadStates.waiting_product)
async def handle_upload_product_text(
    message: Message,
    state: FSMContext,
    user_repo,
) -> None:
    """Handle product text input.

    Args:
        message: Incoming message.
        state: FSM state context.
        user_repo: User repository (injected by middleware).
    """
    user_id = message.from_user.id
    lang = await user_repo.get_lang(user_id) or "ru"

    product = (message.text or "").strip()
    if not product:
        await message.answer(get_text(lang, "admin_ask_product"))
        return

    await state.update_data(product=product)
    await state.set_state(UploadStates.waiting_protocol_no)
    await message.answer(get_text(lang, "admin_ask_protocol_no"))


@router.message(UploadStates.waiting_protocol_no)
async def handle_upload_protocol_no(
    message: Message,
    state: FSMContext,
    protocol_repo,
    user_repo,
    storage_service,
) -> None:
    """Handle protocol number input and complete upload.

    Args:
        message: Incoming message.
        state: FSM state context.
        protocol_repo: Protocol repository (injected by middleware).
        user_repo: User repository (injected by middleware).
        storage_service: Storage service (injected by middleware).
    """
    from bot.keyboards import build_download_keyboard, build_main_inline_keyboard
    from bot.utils.protocol import format_protocol_text

    user_id = message.from_user.id
    lang = await user_repo.get_lang(user_id) or "ru"

    protocol_no = (message.text or "").strip()
    if not protocol_no:
        await message.answer(get_text(lang, "admin_ask_protocol_no"))
        return

    await state.update_data(protocol_no=protocol_no)
    data = await state.get_data()

    try:
        logger.info(
            "Admin {admin} uploading protocol {protocol} ({product}, {year})",
            admin=data.get("uploader"),
            protocol=protocol_no,
            product=data.get("product"),
            year=data.get("year"),
        )

        # Download file from Telegram
        buffer = io.BytesIO()
        file_id = data["file_id"]
        await message.bot.download(file_id, destination=buffer)
        payload = buffer.getvalue()

        # Validate file
        mime = str(data.get("mime") or "").lower()
        filename_raw = str(data.get("filename") or "")
        suffix = Path(filename_raw).suffix.lower()
        if suffix == ".jpeg":
            suffix = ".jpg"

        if suffix not in EXTENSION_TO_MIME:
            raise ValueError("invalid_file")

        resolved_mime = EXTENSION_TO_MIME[suffix]
        stem = Path(filename_raw).stem or "protocol"
        filename = f"{stem}{suffix}"

        file_size = data.get("file_size")
        if isinstance(file_size, int) and file_size > 50 * 1024 * 1024:
            raise ValueError("file_too_large")

        # Save to storage
        from bot.utils import protocol_storage_key
        key = protocol_storage_key(
            year=data["year"],
            product=data["product"],
            protocol_no=protocol_no,
            extension=suffix,
        )

        storage_path = await asyncio.to_thread(
            storage_service.save_bytes, key, payload, resolved_mime
        )
        size_bytes = file_size or storage_path.stat().st_size

        # Create protocol record
        protocol_id = await protocol_repo.create(
            year=data["year"],
            product=data["product"],
            protocol_no=protocol_no,
            storage_key=key,
            filename=filename,
            size_bytes=size_bytes,
            mime=resolved_mime,
            uploaded_by=data["uploader"],
        )

        # Deactivate previous versions
        await protocol_repo.deactivate_prev_versions(
            product=data["product"],
            protocol_no=protocol_no,
            exclude_id=protocol_id,
        )

        # Get created protocol
        protocol = await protocol_repo.get_by_id(protocol_id)
        if protocol is None:
            raise RuntimeError("Failed to read inserted protocol from database")

        # Send success message
        success_text = get_text(lang, "admin_success") + "\n\n" + format_protocol_text(protocol, lang)
        await message.answer(
            success_text,
            reply_markup=build_download_keyboard(protocol.id, lang),
        )

    except ValueError as exc:
        error_key = str(exc)
        if error_key == "invalid_file":
            await message.answer(get_text(lang, "admin_invalid_file"))
        elif error_key == "file_too_large":
            await message.answer(get_text(lang, "admin_file_too_large"))
        else:
            await message.answer(get_text(lang, "admin_error"))
    except Exception:
        logger.exception("Failed to handle admin upload")
        await message.answer(get_text(lang, "admin_error"))
    finally:
        await state.clear()
        await message.answer(
            "Выберите действие:" if lang == "ru" else "Amalni tanlang:",
            reply_markup=build_main_inline_keyboard(lang),
        )


__all__ = ["router"]
