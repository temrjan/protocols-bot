from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.append(str(BASE_DIR))

import uvloop
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from dotenv import load_dotenv
from loguru import logger

from app.bot import create_router
from app.db import Database
from app.storage_local import LocalStorageConfig, configure as configure_storage

LOG_PATH = Path(__file__).resolve().parent.parent / "logs" / "bot.log"
ENV_PATH = Path(__file__).resolve().parent.parent / ".env"

def setup_logging(level: str = "INFO") -> None:
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    logger.remove()
    logger.add(sys.stderr, level=level)
    logger.add(
        LOG_PATH,
        rotation="10 MB",
        retention="14 days",
        enqueue=True,
        level=level,
    )


def require_env(key: str) -> str:
    value = os.getenv(key, "").strip()
    if not value:
        raise RuntimeError(f"Environment variable {key} is required")
    return value


def parse_admins(raw: str | None) -> list[int]:
    if not raw:
        return []
    result: list[int] = []
    for item in raw.split(","):
        item = item.strip()
        if not item:
            continue
        try:
            result.append(int(item))
        except ValueError:
            logger.warning("Skipping invalid admin id: {}", item)
    return result


async def main() -> None:
    load_dotenv(ENV_PATH)
    log_level = os.getenv("LOG_LEVEL", "INFO")
    setup_logging(log_level)

    bot_token = require_env("BOT_TOKEN")
    db_path = require_env("DB_PATH")
    storage_mode = require_env("STORAGE_MODE")
    storage_root = require_env("STORAGE_ROOT")

    admins = parse_admins(os.getenv("ADMINS"))

    if storage_mode.lower() != "local":
        raise RuntimeError(f"Unsupported storage mode: {storage_mode}")

    db = Database(db_path)

    configure_storage(LocalStorageConfig(root=Path(storage_root)))

    bot = Bot(token=bot_token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dispatcher = Dispatcher(storage=MemoryStorage())
    dispatcher.include_router(create_router(db, admins))

    try:
        await db.connect()
        me = await bot.get_me()
        logger.info("ProtocolsBot started as @{username}", username=me.username or me.first_name)
        await dispatcher.start_polling(bot)
    finally:
        logger.info("Shutting down ProtocolsBot")
        await db.close()
        await bot.session.close()


if __name__ == "__main__":
    try:
        uvloop.install()
    except Exception:
        pass
    asyncio.run(main())
