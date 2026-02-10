"""Localization utilities."""

from typing import Dict

TEXT: Dict[str, Dict[str, str]] = {
    "ru": {
        "choose_year": "Выберите год:",
        "choose_product": "Выберите препарат:",
        "no_years": "В базе нет протоколов.",
        "no_products": "Для выбранного года нет протоколов.",
        "no_protocols": "Протоколы не найдены.",
        "error": "Произошла ошибка. Попробуйте позже.",
        "cancelled": "Действие отменено.",
        "upload_success": "Протокол успешно загружен!",
        "moderator_added": "Модератор успешно добавлен.",
        "moderator_exists": "Этот пользователь уже является модератором.",
    },
    "uz": {
        "choose_year": "Yilni tanlang:",
        "choose_product": "Preparatni tanlang:",
        "no_years": "Bazada protokollar yo'q.",
        "no_products": "Tanlangan yil uchun protokollar yo'q.",
        "no_protocols": "Protokollar topilmadi.",
        "error": "Xatolik yuz berdi. Keyinroq urinib ko'ring.",
        "cancelled": "Amal bekor qilindi.",
        "upload_success": "Protokol muvaffaqiyatli yuklandi!",
        "moderator_added": "Moderator muvaffaqiyatli qo'shildi.",
        "moderator_exists": "Bu foydalanuvchi allaqachon moderator.",
    },
}


def get_text(lang: str, key: str) -> str:
    """Get localized text.

    Args:
        lang: Language code ('ru' or 'uz').
        key: Text key.

    Returns:
        Localized text or key if not found.
    """
    return TEXT.get(lang, TEXT["ru"]).get(key, key)
