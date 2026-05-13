"""Storage health-check handler for the primary admin.

Cross-references the protocols and documents tables against files on
disk and reports any drift. Catches silent storage loss before users
notice broken downloads.
"""

import asyncio

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message
from loguru import logger

router = Router(name="admin_health")

MAX_MISSING_PREVIEW = 10

TEXT = {
    "ru": {
        "no_admin": "У вас нет доступа к health-check.",
        "title": "🩺 Здоровье хранилища\n",
        "section_protocols": "Протоколы (active):",
        "section_documents": "Документы:",
        "line_in_db": "  В БД: {n}",
        "line_on_disk": "  На диске: {n}",
        "diff_ok": "  Расхождение: 0 ✓",
        "diff_bad": "  Расхождение: {n} ⚠",
        "missing_header": "\nПервые {shown} из {total} потерянных протоколов:",
        "missing_row": "  • {product} №{protocol_no} ({year})",
        "missing_more": "  …и ещё {n}",
    },
    "uz": {
        "no_admin": "Sizda health-check'ga kirish huquqi yo'q.",
        "title": "🩺 Saqlash sog'lig'i\n",
        "section_protocols": "Protokollar (faol):",
        "section_documents": "Hujjatlar:",
        "line_in_db": "  Bazada: {n}",
        "line_on_disk": "  Diskda: {n}",
        "diff_ok": "  Farq: 0 ✓",
        "diff_bad": "  Farq: {n} ⚠",
        "missing_header": "\n{total} ta yo'qolgan protokoldan birinchi {shown}:",
        "missing_row": "  • {product} №{protocol_no} ({year})",
        "missing_more": "  …va yana {n}",
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


@router.message(Command("admin_health"))
async def handle_admin_health(
    message: Message,
    user_repo,
    protocol_repo,
    document_repo,
    storage_service,
) -> None:
    """Report DB-vs-filesystem drift for protocols and documents.

    Only the primary admin can run this. Counts active rows in each
    table, checks every storage_key against the file on disk, and
    lists up to MAX_MISSING_PREVIEW missing protocol rows so they can
    be re-uploaded.
    """
    from bot.core import settings

    user_id = message.from_user.id
    lang = await user_repo.get_lang(user_id) or "ru"

    if user_id != settings.primary_admin_id:
        await message.answer(get_text(lang, "no_admin"))
        return

    protocols = await protocol_repo.list_active()
    documents = await document_repo.list_all()

    # A few hundred stat() calls — push them off the event loop so
    # polling stays responsive on slow filesystems.
    def _filter_missing_protocols() -> list:
        return [p for p in protocols if not storage_service.exists(p.storage_key)]

    def _filter_missing_documents() -> list:
        return [d for d in documents if not storage_service.exists(d.storage_key)]

    missing_protocols = await asyncio.to_thread(_filter_missing_protocols)
    missing_documents = await asyncio.to_thread(_filter_missing_documents)

    logger.info(
        "Health check by admin {admin}: protocols active={pa} missing={pm}, "
        "documents total={dt} missing={dm}",
        admin=user_id,
        pa=len(protocols),
        pm=len(missing_protocols),
        dt=len(documents),
        dm=len(missing_documents),
    )

    lines: list[str] = [
        get_text(lang, "title"),
        get_text(lang, "section_protocols"),
        get_text(lang, "line_in_db").format(n=len(protocols)),
        get_text(lang, "line_on_disk").format(
            n=len(protocols) - len(missing_protocols)
        ),
        get_text(lang, "diff_ok")
        if not missing_protocols
        else get_text(lang, "diff_bad").format(n=len(missing_protocols)),
        "",
        get_text(lang, "section_documents"),
        get_text(lang, "line_in_db").format(n=len(documents)),
        get_text(lang, "line_on_disk").format(
            n=len(documents) - len(missing_documents)
        ),
        get_text(lang, "diff_ok")
        if not missing_documents
        else get_text(lang, "diff_bad").format(n=len(missing_documents)),
    ]

    if missing_protocols:
        sample = missing_protocols[:MAX_MISSING_PREVIEW]
        lines.append(
            get_text(lang, "missing_header").format(
                shown=len(sample), total=len(missing_protocols)
            )
        )
        for p in sample:
            lines.append(
                get_text(lang, "missing_row").format(
                    product=p.product, protocol_no=p.protocol_no, year=p.year
                )
            )
        remaining = len(missing_protocols) - len(sample)
        if remaining > 0:
            lines.append(get_text(lang, "missing_more").format(n=remaining))

    await message.answer("\n".join(lines))


__all__ = ["router"]
