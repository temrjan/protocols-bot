"""Document upload handlers for admins."""

import contextlib
from pathlib import Path

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder
from loguru import logger

from bot.core.config import settings
from bot.states.admin import AdminStates
from bot.utils import slugify

router = Router(name="admin_upload_document")


@router.callback_query(F.data == "admin:upload_doc")
async def start_document_upload(
    callback: CallbackQuery,
    state: FSMContext,
    user_repo,
    moderator_repo,
) -> None:
    """Start document upload - ask for category name.

    Args:
        callback: Callback query.
        state: FSM context.
        user_repo: User repository.
        moderator_repo: Moderator repository.
    """
    user_id = callback.from_user.id

    # Check if user is admin or moderator
    is_admin = user_id in settings.admin_ids
    is_moderator = await moderator_repo.is_moderator(user_id)

    if not (is_admin or is_moderator):
        await callback.answer("⛔ У вас нет прав доступа", show_alert=True)
        return

    lang = await user_repo.get_lang(user_id) or "ru"

    await state.set_state(AdminStates.waiting_doc_category)
    await state.update_data(lang=lang)

    # Delete previous message
    with contextlib.suppress(Exception):
        await callback.message.delete()

    # Create cancel button
    cancel_builder = InlineKeyboardBuilder()
    cancel_text = "❌ Отменить" if lang == "ru" else "❌ Bekor qilish"
    cancel_builder.button(text=cancel_text, callback_data="cancel_upload")

    await callback.message.answer(
        "Введите название категории документа:\n"
        "(например: 'Регистрационные удостоверения')"
        if lang == "ru"
        else "Hujjat kategoriyasi nomini kiriting:\n"
        "(masalan: 'Ro'yxatdan o'tkazish guvohnomalari')",
        reply_markup=cancel_builder.as_markup(),
    )
    await callback.answer()


@router.callback_query(F.data == "cancel_upload")
async def handle_cancel_upload(
    callback: CallbackQuery,
    state: FSMContext,
) -> None:
    """Handle cancel button.

    Args:
        callback: Callback query.
        state: FSM context.
    """
    await state.clear()
    with contextlib.suppress(Exception):
        await callback.message.delete()
    await callback.answer(
        "Загрузка отменена"
        if callback.from_user.language_code == "ru"
        else "Yuklash bekor qilindi"
    )


@router.message(AdminStates.waiting_doc_category, F.text)
async def handle_doc_category(
    message: Message,
    state: FSMContext,
) -> None:
    """Handle category name input - ask for file.

    Args:
        message: Message with category name.
        state: FSM context.
    """
    category = message.text.strip()
    lang = (await state.get_data()).get("lang") or "ru"

    await state.update_data(category=category)
    await state.set_state(AdminStates.waiting_doc_file)

    # Create cancel button
    cancel_builder = InlineKeyboardBuilder()
    cancel_text = "❌ Отменить" if lang == "ru" else "❌ Bekor qilish"
    cancel_builder.button(text=cancel_text, callback_data="cancel_upload")

    await message.answer(
        f"Категория: <b>{category}</b>\n\nОтправьте файл документа (PDF, JPG, PNG):"
        if lang == "ru"
        else f"Kategoriya: <b>{category}</b>\n\n"
        f"Hujjat faylini yuboring (PDF, JPG, PNG):",
        reply_markup=cancel_builder.as_markup(),
    )


@router.message(AdminStates.waiting_doc_file, F.document | F.photo)
async def handle_doc_file(
    message: Message,
    state: FSMContext,
    document_repo,
    user_repo,
) -> None:
    """Handle file upload - save document.

    Args:
        message: Message with file.
        state: FSM context.
        document_repo: Document repository.
        user_repo: User repository.
    """

    from bot.core import bot
    from bot.core.config import settings
    from bot.services.storage import StorageService

    data = await state.get_data()
    category = data["category"]
    lang = data.get("lang") or "ru"

    # Get file info
    if message.document:
        file_id = message.document.file_id
        filename = message.document.file_name
        mime = message.document.mime_type or "application/pdf"
        size_bytes = message.document.file_size
    else:  # photo
        file_id = message.photo[-1].file_id
        filename = f"{slugify(category)}.jpg"
        mime = "image/jpeg"
        size_bytes = message.photo[-1].file_size

    # Download file
    file = await bot.get_file(file_id)
    file_data = await bot.download_file(file.file_path)
    file_bytes = file_data.read()

    # Generate storage key. Sanitize the filename before use: StorageService
    # already rejects path-traversal keys, but slugifying the stem keeps the
    # key ASCII-only and predictable regardless of what Telegram delivered.
    suffix = Path(filename).suffix.lower() or ".bin"
    stem_slug = slugify(Path(filename).stem) or "document"
    storage_key = f"documents/{slugify(category)}/{stem_slug}{suffix}"

    # Save to storage
    storage = StorageService(settings.storage_root)
    await storage.save_bytes(storage_key, file_bytes, mime)

    # Save to database
    try:
        query = """
            INSERT INTO documents
            (category, filename, storage_key, size_bytes, mime, tg_file_id, uploaded_by)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """
        await document_repo.conn.execute(
            query,
            (
                category,
                filename,
                storage_key,
                size_bytes,
                mime,
                file_id,
                message.from_user.id,
            ),
        )
        await document_repo.conn.commit()

        await state.clear()

        success_msg = (
            f"✅ Документ успешно загружен!\n\n"
            f"Категория: <b>{category}</b>\n"
            f"Файл: {filename}"
            if lang == "ru"
            else f"✅ Hujjat muvaffaqiyatli yuklandi!\n\n"
            f"Kategoriya: <b>{category}</b>\n"
            f"Fayl: {filename}"
        )

        await message.answer(success_msg)

        logger.info(
            f"Document uploaded: category='{category}', file='{filename}' by {message.from_user.id}"
        )

    except Exception as e:
        logger.exception(f"Failed to save document: {e}")
        await state.clear()
        await message.answer(
            "❌ Ошибка при сохранении документа. Попробуйте позже."
            if lang == "ru"
            else "❌ Xatolik yuz berdi. Keyinroq urinib ko'ring."
        )


__all__ = ["router"]
