"""Additional documents handlers for users.

This module contains handlers for viewing and downloading additional documents.
"""

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder

router = Router(name="user_documents")

TEXT = {
    "ru": {
        "choose_category": "Выберите категорию документов:",
        "no_categories": "Документы не найдены.",
        "no_documents": "В этой категории нет документов.",
    },
    "uz": {
        "choose_category": "Hujjat kategoriyasini tanlang:",
        "no_categories": "Hujjatlar topilmadi.",
        "no_documents": "Bu kategoriyada hujjatlar yo'q.",
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


@router.callback_query(F.data == "menu:documents")
async def handle_documents_menu(
    callback: CallbackQuery,
    state: FSMContext,
    document_repo,
    user_repo,
) -> None:
    """Handle documents menu callback - show categories.

    Args:
        callback: Callback query.
        state: FSM state context.
        document_repo: Document repository.
        user_repo: User repository.
    """
    from bot.handlers.user.menus import start_documents_flow

    user_id = callback.from_user.id
    lang = await user_repo.get_lang(user_id) or "ru"

    await callback.answer()
    await start_documents_flow(
        callback.message, state, lang=lang, document_repo=document_repo
    )


@router.callback_query(F.data.startswith("doc_cat:"))
async def handle_category_selection(
    callback: CallbackQuery,
    document_repo,
    user_repo,
) -> None:
    """Handle category selection - show documents in category.

    Args:
        callback: Callback query.
        document_repo: Document repository.
        user_repo: User repository.
    """
    user_id = callback.from_user.id
    lang = await user_repo.get_lang(user_id) or "ru"

    try:
        idx = int(callback.data.split(":", 1)[1])
    except ValueError:
        await callback.answer("Invalid category", show_alert=True)
        return

    categories = await document_repo.get_categories()
    if not 0 <= idx < len(categories):
        await callback.answer(get_text(lang, "no_documents"), show_alert=True)
        return

    category = categories[idx]

    # Get documents in category
    documents = await document_repo.find_by_category(category)

    if not documents:
        await callback.answer(get_text(lang, "no_documents"), show_alert=True)
        return

    from bot.utils import safe_send_many

    download_text = "📥 Скачать" if lang == "ru" else "📥 Yuklab olish"

    def _build(doc):
        builder = InlineKeyboardBuilder()
        builder.button(text=download_text, callback_data=f"download_doc:{doc.id}")
        text = (
            f"📄 <b>{doc.filename}</b>\nКатегория: {category}"
            if lang == "ru"
            else f"📄 <b>{doc.filename}</b>\nKategoriya: {category}"
        )
        return text, builder.as_markup()

    await safe_send_many(callback.message, documents, _build)
    await callback.answer()


@router.callback_query(F.data.startswith("download_doc:"))
async def handle_document_download(
    callback: CallbackQuery,
    document_repo,
    user_repo,
) -> None:
    """Handle document download callback.

    Args:
        callback: Callback query.
        document_repo: Document repository.
        user_repo: User repository.
    """
    from aiogram.types import FSInputFile

    from bot.core.config import settings
    from bot.services.storage import StorageService

    user_id = callback.from_user.id
    lang = await user_repo.get_lang(user_id) or "ru"

    try:
        doc_id = int(callback.data.split(":", 1)[1])
    except ValueError:
        await callback.answer("Invalid request", show_alert=True)
        return

    # Get document by ID
    document = await document_repo.get_by_id(doc_id)
    if document is None:
        await callback.answer(get_text(lang, "no_documents"), show_alert=True)
        return

    await callback.answer("Готовим файл…" if lang == "ru" else "Fayl tayyorlanmoqda…")

    # Send document file
    from aiogram.exceptions import TelegramBadRequest
    from loguru import logger

    try:
        # Try cached file_id; on stale ID, invalidate and re-upload from storage.
        if document.tg_file_id:
            try:
                await callback.message.answer_document(
                    document=document.tg_file_id,
                    caption=f"📄 {document.filename}",
                )
                return
            except TelegramBadRequest as exc:
                logger.warning(
                    "Stale tg_file_id for document {id}: {err}; re-uploading",
                    id=doc_id,
                    err=exc.message,
                )
                await document_repo.update_file_id(doc_id, None)

        # Load from storage
        storage = StorageService(settings.storage_root)
        file_path = storage.root / document.storage_key

        if not file_path.exists():
            await callback.message.answer(
                "Файл не найден" if lang == "ru" else "Fayl topilmadi"
            )
            return

        # Send file
        input_file = FSInputFile(file_path, filename=document.filename)
        sent = await callback.message.answer_document(
            document=input_file,
            caption=f"📄 {document.filename}",
        )

        # Save file_id for future use
        if sent.document:
            await document_repo.update_file_id(doc_id, sent.document.file_id)

    except Exception as e:
        logger.exception(f"Failed to send document {doc_id}: {e}")
        await callback.message.answer(
            "Ошибка при отправке файла" if lang == "ru" else "Fayl yuborishda xatolik"
        )


__all__ = ["router"]
