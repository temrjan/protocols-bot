"""Document formatting and display utilities."""

import html

from aiogram.types import Message

from bot.database.models import Document

# Label translations
LABELS = {
    "ru": {
        "name": "Название",
        "type": "Тип",
        "uploaded": "Загружено",
        "filename": "Файл",
    },
    "uz": {
        "name": "Nomi",
        "type": "Turi",
        "uploaded": "Yuklangan",
        "filename": "Fayl",
    },
}

# Text constants
TEXT = {
    "ru": {
        "no_documents": "Документы не найдены.",
        "download_button": "Скачать",
    },
    "uz": {
        "no_documents": "Hujjatlar topilmadi.",
        "download_button": "Yuklab olish",
    },
}


def get_labels(lang: str) -> dict[str, str]:
    """Get label translations for language.

    Args:
        lang: Language code ('ru' or 'uz').

    Returns:
        Dictionary of label translations.
    """
    return LABELS.get(lang, LABELS["ru"])


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


def format_document_text(document: Document, lang: str) -> str:
    """Format document information as text.

    Args:
        document: Document database model.
        lang: Language code ('ru' or 'uz').

    Returns:
        Formatted document information.
    """
    labels = get_labels(lang)
    uploaded_at = document.uploaded_at
    return (
        f"{labels['name']}: {html.escape(document.product)}\n"
        f"{labels['type']}: {html.escape(document.doc_type)}\n"
        f"{labels['filename']}: {html.escape(document.filename)}\n"
        f"{labels['uploaded']}: {uploaded_at}"
    )


async def send_document_list(
    message: Message,
    documents: list[Document],
    lang: str,
) -> None:
    """Send list of documents to user.

    Args:
        message: Message to reply to.
        documents: List of document models.
        lang: Language code ('ru' or 'uz').
    """
    from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

    if not documents:
        await message.answer(get_text(lang, "no_documents"))
        return

    for document in documents:
        caption = format_document_text(document, lang)
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text=get_text(lang, "download_button"),
                        callback_data=f"download_doc:{document.id}",
                    )
                ]
            ]
        )
        await message.answer(caption, reply_markup=keyboard)


async def send_document_file(
    message: Message,
    document: Document,
    lang: str,
) -> None:
    """Send document file to user.

    Args:
        message: Message to reply to.
        document: Document database model.
        lang: Language code ('ru' or 'uz').
    """
    # This is a placeholder - actual implementation will depend on storage service
    # For now, just send the document info
    caption = format_document_text(document, lang)
    await message.answer(f"Document file:\n{caption}")


__all__ = ["format_document_text", "send_document_file", "send_document_list"]
