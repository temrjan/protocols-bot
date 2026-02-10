from __future__ import annotations

import asyncio
import html
import io
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, Sequence, Set

from aiogram import F, Router
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    CallbackQuery,
    FSInputFile,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)
from aiogram.utils.keyboard import InlineKeyboardBuilder
from loguru import logger

from app import utils
from app.db import Database, ProtocolRecord
from app.storage_local import open_path, save_bytes


ALLOWED_MIME_TYPES: Dict[str, tuple[str, ...]] = {
    "application/pdf": (".pdf",),
    "image/jpeg": (".jpg", ".jpeg"),
    "image/jpg": (".jpg", ".jpeg"),
}

EXTENSION_TO_MIME: Dict[str, str] = {
    ".pdf": "application/pdf",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
}

PRODUCT_NAMES: Sequence[str] = (
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


class FilterStates(StatesGroup):
    choosing_year = State()
    choosing_product = State()


class SearchState(StatesGroup):
    waiting_text = State()


class UploadStates(StatesGroup):
    waiting_year = State()
    choosing_product = State()
    waiting_product = State()
    waiting_protocol_no = State()


class AdminStates(StatesGroup):
    waiting_moderator_id = State()


TEXT = {
    "ru": {
        "language_prompt": "Выберите язык / Tilni tanlang:",
        "main_menu": "Выберите действие:",
        "filters_button": "Найти по фильтрам",
        "search_button": "Поиск по номеру",
        "choose_year": "Выберите год.",
        "choose_product": "Выберите препарат.",
        "no_years": "В базе пока нет доступных протоколов.",
        "no_products": "Для выбранного года протоколы не найдены.",
        "no_protocols": "Протоколы не найдены.",
        "ask_search_text": "Введите номер протокола или название препарата.",
        "search_no_results": "По вашему запросу ничего не найдено.",
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
        "cancelled": "Действие отменено.",
        "nothing_to_cancel": "Нет активного процесса.",
        "download_error": "Не удалось получить файл. Попробуйте позже.",
        "download_button": "Скачать",
        "fetching": "Готовим файл…",
        "admin_menu_title": "Админ-панель. Выберите действие:",
        "admin_menu_upload": "Загрузить протокол",
        "admin_menu_add_mod": "Назначить модератора",
        "admin_upload_hint": "Чтобы загрузить протокол, отправьте PDF или JPG-файл в чат.",
        "admin_enter_moderator": "Введите Telegram ID пользователя, которому нужно выдать права загрузки.",
        "admin_invalid_id": "Введите корректный числовой Telegram ID.",
        "admin_moderator_added": "Пользователь {id} назначен модератором и теперь может загружать протоколы.",
        "admin_moderator_exists": "Этот пользователь уже имеет права для загрузки протоколов.",
        "admin_not_primary": "У вас нет доступа к админ-панели.",
    },
    "uz": {
        "language_prompt": "Tilni tanlang:",
        "main_menu": "Amalni tanlang:",
        "filters_button": "Filtr bo'yicha qidirish",
        "search_button": "Raqam bo'yicha qidirish",
        "choose_year": "Yilni tanlang.",
        "choose_product": "Preparatni tanlang.",
        "no_years": "Bazadda protokollar topilmadi.",
        "no_products": "Tanlangan yil uchun protokollar yo'q.",
        "no_protocols": "Hech narsa topilmadi.",
        "ask_search_text": "Protokol raqamini yoki preparat nomini kiriting.",
        "search_no_results": "Sizning so'rovingiz bo'yicha ma'lumot topilmadi.",
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
        "cancelled": "Amal bekor qilindi.",
        "nothing_to_cancel": "Faol jarayon yo'q.",
        "download_error": "Faylni olishning imkoni bo'lmadi. Keyinroq qayta urinib ko'ring.",
        "download_button": "Yuklab olish",
        "fetching": "Fayl tayyorlanmoqda…",
        "admin_menu_title": "Admin panel. Amalni tanlang:",
        "admin_menu_upload": "Protokolni yuklash",
        "admin_menu_add_mod": "Moderator tayinlash",
        "admin_upload_hint": "Protokolni yuklash uchun PDF yoki JPG faylini shu chatga yuboring.",
        "admin_enter_moderator": "Moderator qilish kerak bo'lgan foydalanuvchining Telegram ID raqamini kiriting.",
        "admin_invalid_id": "Iltimos, to'g'ri raqamli Telegram ID kiriting.",
        "admin_moderator_added": "{id} foydalanuvchi moderator etib tayinlandi va endi protokollarni yuklashi mumkin.",
        "admin_moderator_exists": "Bu foydalanuvchi allaqachon yuklash huquqiga ega.",
        "admin_not_primary": "Sizda admin panelga kirish huquqi yo'q.",
    },
}


LABELS = {
    "ru": {
        "product": "Продукт",
        "protocol": "Протокол",
        "year": "Год",
        "uploaded": "Загружено",
        "filename": "Файл",
        "size": "Размер",
    },
    "uz": {
        "product": "Mahsulot",
        "protocol": "Protokol",
        "year": "Yil",
        "uploaded": "Yuklangan",
        "filename": "Fayl",
        "size": "Hajmi",
    },
}


def get_text(lang: str, key: str) -> str:
    base = TEXT["ru"]
    data = TEXT.get(lang, base)
    return data.get(key, base.get(key, key))


def get_labels(lang: str) -> Dict[str, str]:
    return LABELS.get(lang, LABELS["ru"])


def shorten(text: str, limit: int = 32) -> str:
    if len(text) <= limit:
        return text
    return text[: limit - 3] + "..."


def format_size(value: int | None) -> str:
    if value is None:
        return "-"
    size = float(value)
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if size < 1024 or unit == "TB":
            if unit == "B":
                return f"{int(size)} B"
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{int(value)} B"


def format_protocol_text(record: ProtocolRecord, lang: str) -> str:
    labels = get_labels(lang)
    uploaded_at = record.uploaded_at
    return (
        f"{labels['product']}: {html.escape(record.product)}\n"
        f"{labels['protocol']}: {html.escape(record.protocol_no)}\n"
        f"{labels['year']}: {record.year}\n"
        f"{labels['filename']}: {html.escape(record.filename)}\n"
        f"{labels['uploaded']}: {uploaded_at}"
    )


async def fetch_from_local(record: ProtocolRecord) -> FSInputFile:
    path = await asyncio.to_thread(open_path, record.storage_key)
    extension = Path(record.storage_key).suffix or ".pdf"
    filename = record.filename or f"{record.protocol_no}{extension}"
    return FSInputFile(path, filename=filename)


async def send_protocol_list(message: Message, protocols: Sequence[ProtocolRecord], lang: str) -> None:
    if not protocols:
        await message.answer(get_text(lang, "no_protocols"))
        return

    for record in protocols:
        caption = format_protocol_text(record, lang)
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text=get_text(lang, "download_button"),
                        callback_data=f"download:{record.id}",
                    )
                ]
            ]
        )
        await message.answer(caption, reply_markup=keyboard)


def create_router(db: Database, admins: Sequence[int]) -> Router:
    router = Router()
    uploader_ids: Set[int] = set(admins)
    moderators: Set[int] = set()
    user_languages: Dict[int, str] = {}
    primary_admin = admins[0] if admins else None

    def get_predefined_products() -> list[str]:
        return [item.strip() for item in PRODUCT_NAMES if item.strip()]

    def build_product_keyboard(products: Sequence[str]) -> InlineKeyboardMarkup:
        builder = InlineKeyboardBuilder()
        for idx, product in enumerate(products):
            builder.button(text=shorten(product), callback_data=f"upload_product:{idx}")
        builder.adjust(1)
        return builder.as_markup()

    def build_year_keyboard() -> InlineKeyboardMarkup:
        builder = InlineKeyboardBuilder()
        current_year = datetime.now().year
        builder.button(text=str(current_year), callback_data=f"upload_year:{current_year}")
        previous_year = current_year - 1
        builder.button(text=str(previous_year), callback_data=f"upload_year:{previous_year}")
        builder.adjust(2)
        return builder.as_markup()

    async def proceed_after_year(message: Message, state: FSMContext, lang: str, year: int) -> None:
        await state.update_data(year=year)
        products = get_predefined_products()
        if products:
            await state.update_data(products=products)
            await state.set_state(UploadStates.choosing_product)
            await message.answer(get_text(lang, "admin_choose_product"), reply_markup=build_product_keyboard(products))
        else:
            await state.update_data(products=[])
            await state.set_state(UploadStates.waiting_product)
            await message.answer(get_text(lang, "admin_ask_product"))

    async def send_main_menu(message: Message, lang: str) -> None:
        builder = InlineKeyboardBuilder()
        builder.button(
            text=get_text(lang, "filters_button"),
            callback_data="menu:filters",
        )
        builder.button(
            text=get_text(lang, "search_button"),
            callback_data="menu:search",
        )
        builder.adjust(1)
        await message.answer(get_text(lang, "main_menu"), reply_markup=builder.as_markup())

    async def get_lang(user_id: int) -> str:
        if user_id in user_languages:
            return user_languages[user_id]
        lang = await db.get_user_lang(user_id)
        if lang:
            user_languages[user_id] = lang
            return lang
        return "ru"

    async def set_lang(user_id: int, lang: str) -> None:
        user_languages[user_id] = lang
        await db.set_user_lang(user_id, lang)

    async def ensure_moderators_loaded() -> None:
        if not moderators:
            existing = await db.list_moderators()
            moderators.update(existing)
            uploader_ids.update(existing)

    def has_upload_rights(user_id: int) -> bool:
        return user_id in uploader_ids

    async def complete_upload(message: Message, data: Dict[str, object]) -> ProtocolRecord:
        buffer = io.BytesIO()
        file_id = data["file_id"]  # type: ignore[index]
        await message.bot.download(file_id, destination=buffer)
        payload = buffer.getvalue()

        mime = str(data.get("mime") or "").lower()
        filename_raw = str(data.get("filename") or "")
        suffix = Path(filename_raw).suffix.lower()
        if suffix == ".jpeg":
            suffix = ".jpg"

        if mime:
            if mime in ALLOWED_MIME_TYPES:
                allowed_suffixes = ALLOWED_MIME_TYPES[mime]
                if suffix not in allowed_suffixes:
                    suffix = allowed_suffixes[0]
            elif suffix in EXTENSION_TO_MIME:
                mime = EXTENSION_TO_MIME[suffix]
            else:
                raise ValueError("invalid_file")
        else:
            if suffix in EXTENSION_TO_MIME:
                mime = EXTENSION_TO_MIME[suffix]
            else:
                raise ValueError("invalid_file")

        if suffix not in EXTENSION_TO_MIME:
            raise ValueError("invalid_file")

        resolved_mime = EXTENSION_TO_MIME[suffix]

        stem = Path(filename_raw).stem or "protocol"
        filename = f"{stem}{suffix}"

        file_size = data.get("file_size")
        if isinstance(file_size, int) and file_size > 50 * 1024 * 1024:
            raise ValueError("file_too_large")

        key = utils.protocol_storage_key(
            year=data["year"],  # type: ignore[index]
            product=data["product"],  # type: ignore[index]
            protocol_no=data["protocol_no"],  # type: ignore[index]
            extension=suffix,
        )

        storage_path = await asyncio.to_thread(save_bytes, key, payload, resolved_mime)
        size_bytes = file_size or storage_path.stat().st_size

        protocol_id = await db.insert_protocol(
            year=data["year"],  # type: ignore[index]
            product=data["product"],  # type: ignore[index]
            protocol_no=data["protocol_no"],  # type: ignore[index]
            storage_key=key,
            filename=filename,
            size_bytes=size_bytes,
            mime=resolved_mime,
            uploaded_by=data["uploader"],  # type: ignore[index]
        )

        await db.deactivate_prev_versions(
            product=data["product"],  # type: ignore[index]
            protocol_no=data["protocol_no"],  # type: ignore[index]
            exclude_id=protocol_id,
        )
        record = await db.get_by_id(protocol_id)
        if record is None:
            raise RuntimeError("Failed to read inserted protocol from database")
        return record

    @router.message(CommandStart())
    async def handle_start(message: Message, state: FSMContext) -> None:
        await state.clear()
        await set_lang(message.from_user.id, "ru")
        keyboard = InlineKeyboardBuilder()
        keyboard.button(text="🇷🇺 Русский", callback_data="lang:ru")
        keyboard.button(text="🇺🇿 O'zbekcha", callback_data="lang:uz")
        keyboard.adjust(1)
        await message.answer(
            TEXT["ru"]["language_prompt"],
            reply_markup=keyboard.as_markup(),
        )

    @router.message(Command("cancel"))
    async def handle_cancel(message: Message, state: FSMContext) -> None:
        lang = await get_lang(message.from_user.id)
        current = await state.get_state()
        if current is None:
            await message.answer(get_text(lang, "nothing_to_cancel"))
            return
        await state.clear()
        await message.answer(get_text(lang, "cancelled"))
        await send_main_menu(message, lang)

    @router.callback_query(F.data.startswith("lang:"))
    async def handle_language(callback: CallbackQuery, state: FSMContext) -> None:
        lang_code = callback.data.split(":", 1)[1]
        lang = lang_code if lang_code in TEXT else "ru"
        await set_lang(callback.from_user.id, lang)
        try:
            await callback.message.edit_reply_markup()
        except Exception:
            pass
        await callback.answer()
        await state.clear()
        await send_main_menu(callback.message, lang)

    @router.callback_query(F.data == "menu:filters")
    async def handle_filters(callback: CallbackQuery, state: FSMContext) -> None:
        lang = await get_lang(callback.from_user.id)
        await state.clear()
        years = await db.list_years()
        if not years:
            await callback.answer(get_text(lang, "no_years"), show_alert=True)
            return
        builder = InlineKeyboardBuilder()
        for year in years:
            builder.button(text=str(year), callback_data=f"year:{year}")
        builder.adjust(2)
        await state.set_state(FilterStates.choosing_year)
        await callback.message.answer(get_text(lang, "choose_year"), reply_markup=builder.as_markup())
        await callback.answer()

    @router.callback_query(FilterStates.choosing_year, F.data.startswith("year:"))
    async def handle_year(callback: CallbackQuery, state: FSMContext) -> None:
        lang = await get_lang(callback.from_user.id)
        try:
            year = int(callback.data.split(":", 1)[1])
        except ValueError:
            await callback.answer("Invalid year", show_alert=True)
            return
        products = get_predefined_products()
        if not products:
            products = await db.list_products(year)
        if not products:
            await callback.answer(get_text(lang, "no_products"), show_alert=True)
            return
        builder = InlineKeyboardBuilder()
        for idx, product in enumerate(products):
            builder.button(text=shorten(product), callback_data=f"product:{idx}")
        builder.adjust(1)
        await state.update_data(selected_year=year, products=products)
        await state.set_state(FilterStates.choosing_product)
        await callback.message.answer(get_text(lang, "choose_product"), reply_markup=builder.as_markup())
        await callback.answer()

    @router.callback_query(FilterStates.choosing_product, F.data.startswith("product:"))
    async def handle_product(callback: CallbackQuery, state: FSMContext) -> None:
        lang = await get_lang(callback.from_user.id)
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
        year = data.get("selected_year")
        await state.clear()
        protocols = await db.find_by_filters(year=year, product=product)
        await send_protocol_list(callback.message, protocols, lang)
        await send_main_menu(callback.message, lang)
        await callback.answer()

    @router.callback_query(F.data == "menu:search")
    async def handle_search(callback: CallbackQuery, state: FSMContext) -> None:
        lang = await get_lang(callback.from_user.id)
        await state.set_state(SearchState.waiting_text)
        await callback.message.answer(get_text(lang, "ask_search_text"))
        await callback.answer()

    @router.message(SearchState.waiting_text)
    async def handle_search_text(message: Message, state: FSMContext) -> None:
        lang = await get_lang(message.from_user.id)
        raw_query = message.text or ""
        query = raw_query.strip()
        await state.clear()
        if not query:
            await message.answer(get_text(lang, "ask_search_text"))
            await send_main_menu(message, lang)
            return
        protocols: Sequence[ProtocolRecord] = []
        year_match = re.match(r"^(\d{4})\s+(.+)$", query)
        if year_match:
            try:
                year_value = int(year_match.group(1))
            except ValueError:
                year_value = None
            protocol_fragment = year_match.group(2).strip()
            if year_value is not None and protocol_fragment:
                protocols = await db.find_by_year_and_protocol(year_value, protocol_fragment)
        if not protocols:
            protocols = await db.find_by_code(query)
        if not protocols:
            await message.answer(get_text(lang, "search_no_results"))
        else:
            await send_protocol_list(message, protocols, lang)
        await send_main_menu(message, lang)

    @router.message(Command("admin"))
    async def handle_admin_menu(message: Message, state: FSMContext) -> None:
        lang = await get_lang(message.from_user.id)
        if message.from_user.id != primary_admin:
            await message.answer(get_text(lang, "admin_not_primary"))
            return
        await state.clear()
        builder = InlineKeyboardBuilder()
        builder.button(text=get_text(lang, "admin_menu_upload"), callback_data="admin:upload")
        builder.button(text=get_text(lang, "admin_menu_add_mod"), callback_data="admin:add_mod")
        builder.adjust(1)
        await message.answer(get_text(lang, "admin_menu_title"), reply_markup=builder.as_markup())

    @router.callback_query(F.data == "admin:upload")
    async def handle_admin_upload(callback: CallbackQuery, state: FSMContext) -> None:
        lang = await get_lang(callback.from_user.id)
        if callback.from_user.id != primary_admin:
            await callback.answer(get_text(lang, "admin_not_primary"), show_alert=True)
            return
        await state.clear()
        await callback.answer()
        await callback.message.answer(get_text(lang, "admin_upload_hint"))

    @router.callback_query(F.data == "admin:add_mod")
    async def handle_admin_add_moderator(callback: CallbackQuery, state: FSMContext) -> None:
        lang = await get_lang(callback.from_user.id)
        if callback.from_user.id != primary_admin:
            await callback.answer(get_text(lang, "admin_not_primary"), show_alert=True)
            return
        await state.set_state(AdminStates.waiting_moderator_id)
        await callback.answer()
        await callback.message.answer(get_text(lang, "admin_enter_moderator"))

    @router.message(AdminStates.waiting_moderator_id)
    async def handle_admin_moderator_id(message: Message, state: FSMContext) -> None:
        lang = await get_lang(message.from_user.id)
        if message.from_user.id != primary_admin:
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
        await ensure_moderators_loaded()
        if moderator_id in uploader_ids:
            await message.answer(get_text(lang, "admin_moderator_exists"))
            await state.clear()
            await send_main_menu(message, lang)
            return
        added = await db.add_moderator(moderator_id)
        if added:
            moderators.add(moderator_id)
            uploader_ids.add(moderator_id)
            await message.answer(get_text(lang, "admin_moderator_added").format(id=moderator_id))
        else:
            await ensure_moderators_loaded()
            await message.answer(get_text(lang, "admin_moderator_exists"))
        await state.clear()
        await send_main_menu(message, lang)

    async def prepare_upload(
        message: Message,
        state: FSMContext,
        *,
        file_id: str,
        filename: str,
        mime: str,
        file_size: int | None,
    ) -> None:
        lang = await get_lang(message.from_user.id)
        await state.clear()
        await state.update_data(
            file_id=file_id,
            filename=filename,
            mime=mime,
            file_size=file_size,
            uploader=message.from_user.id,
        )
        await state.set_state(UploadStates.waiting_year)
        await message.answer(get_text(lang, "admin_start"), reply_markup=build_year_keyboard())

    @router.callback_query(F.data.startswith("download:"))
    async def handle_download(callback: CallbackQuery) -> None:
        lang = await get_lang(callback.from_user.id)
        try:
            protocol_id = int(callback.data.split(":", 1)[1])
        except ValueError:
            await callback.answer("Invalid request", show_alert=True)
            return
        record = await db.get_by_id(protocol_id)
        if record is None:
            await callback.answer(get_text(lang, "no_protocols"), show_alert=True)
            return
        await callback.answer(get_text(lang, "fetching"))
        try:
            caption = format_protocol_text(record, lang)
            if record.tg_file_id:
                if record.mime.startswith("image/"):
                    await callback.message.answer_photo(record.tg_file_id, caption=caption)
                else:
                    await callback.message.answer_document(record.tg_file_id, caption=caption)
                return
            document = await fetch_from_local(record)
            if record.mime.startswith("image/"):
                sent = await callback.message.answer_photo(document, caption=caption)
                file_id = sent.photo[-1].file_id if sent.photo else None
            else:
                sent = await callback.message.answer_document(document, caption=caption)
                file_id = sent.document.file_id if sent.document else None
            if file_id:
                await db.set_tg_file_id(record.id, file_id)
            else:
                logger.warning("Telegram did not return media info for protocol {protocol_id}", protocol_id=record.id)
        except Exception:
            logger.exception("Failed to deliver protocol %s", protocol_id)
            await callback.message.answer(get_text(lang, "download_error"))

    @router.message(F.document)
    async def handle_document(message: Message, state: FSMContext) -> None:
        lang = await get_lang(message.from_user.id)
        await ensure_moderators_loaded()
        if not has_upload_rights(message.from_user.id):
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
        await prepare_upload(
            message,
            state,
            file_id=document.file_id,
            filename=filename,
            mime=mime or "",
            file_size=document.file_size,
        )

    @router.message(F.photo)
    async def handle_photo(message: Message, state: FSMContext) -> None:
        lang = await get_lang(message.from_user.id)
        await ensure_moderators_loaded()
        if not has_upload_rights(message.from_user.id):
            await message.answer(get_text(lang, "not_admin"))
            return
        if not message.photo:
            await message.answer(get_text(lang, "admin_invalid_file"))
            return
        photo = message.photo[-1]
        filename = f"protocol-{photo.file_unique_id}.jpg"
        await prepare_upload(
            message,
            state,
            file_id=photo.file_id,
            filename=filename,
            mime="image/jpeg",
            file_size=photo.file_size,
        )

    @router.message(UploadStates.waiting_year)
    async def handle_upload_year(message: Message, state: FSMContext) -> None:
        lang = await get_lang(message.from_user.id)
        if not has_upload_rights(message.from_user.id):
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
    async def handle_upload_year_choice(callback: CallbackQuery, state: FSMContext) -> None:
        lang = await get_lang(callback.from_user.id)
        if not has_upload_rights(callback.from_user.id):
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
    async def handle_upload_product_prompt(message: Message, state: FSMContext) -> None:
        lang = await get_lang(message.from_user.id)
        if not has_upload_rights(message.from_user.id):
            await state.clear()
            await message.answer(get_text(lang, "not_admin"))
            return
        data = await state.get_data()
        products = data.get("products", [])
        if not products:
            await state.set_state(UploadStates.waiting_product)
            await message.answer(get_text(lang, "admin_ask_product"))
            return
        await message.answer(get_text(lang, "admin_choose_product"), reply_markup=build_product_keyboard(products))

    @router.callback_query(UploadStates.choosing_product, F.data.startswith("upload_product:"))
    async def handle_upload_product_choice(callback: CallbackQuery, state: FSMContext) -> None:
        lang = await get_lang(callback.from_user.id)
        if not has_upload_rights(callback.from_user.id):
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
    async def handle_upload_product(message: Message, state: FSMContext) -> None:
        lang = await get_lang(message.from_user.id)
        product = (message.text or "").strip()
        if not product:
            await message.answer(get_text(lang, "admin_ask_product"))
            return
        await state.update_data(product=product)
        await state.set_state(UploadStates.waiting_protocol_no)
        await message.answer(get_text(lang, "admin_ask_protocol_no"))

    @router.message(UploadStates.waiting_protocol_no)
    async def handle_upload_protocol_no(message: Message, state: FSMContext) -> None:
        lang = await get_lang(message.from_user.id)
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
            record = await complete_upload(message, data)
            success_text = get_text(lang, "admin_success") + "\n\n" + format_protocol_text(record, lang)
            keyboard = InlineKeyboardMarkup(
                inline_keyboard=[
                    [
                        InlineKeyboardButton(
                            text=get_text(lang, "download_button"),
                            callback_data=f"download:{record.id}",
                        )
                    ]
                ]
            )
            await message.answer(success_text, reply_markup=keyboard)
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
            await send_main_menu(message, lang)

    return router


__all__ = ["create_router"]
