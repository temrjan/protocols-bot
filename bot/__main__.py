"""Bot entry point."""

import asyncio
import contextlib
import sys

from aiogram import Bot
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.storage.redis import RedisStorage
from aiogram.types import BotCommand, BotCommandScopeDefault
from loguru import logger

from bot.core import bot, dp, settings, setup_logging
from bot.database import Database

# Import routers
from bot.handlers import admin, common, download, user

# Import middlewares
from bot.middlewares import DatabaseMiddleware, LoggingMiddleware, ThrottlingMiddleware

# Import services
from bot.services import StorageService


async def set_commands(bot_instance: Bot) -> None:
    """Set bot commands.

    Args:
        bot_instance: Bot instance.
    """
    commands = [
        BotCommand(command="start", description="🚀 Запустить бота"),
        BotCommand(command="cancel", description="❌ Отменить"),
        BotCommand(command="admin", description="⚙️ Админ-панель"),
    ]
    await bot_instance.set_my_commands(commands, scope=BotCommandScopeDefault())


async def on_startup() -> None:
    """Startup actions."""
    logger.info("Bot started successfully")
    logger.info(f"Admin IDs: {settings.admin_ids}")
    logger.info(f"Database: {settings.db_path}")
    logger.info(f"Storage: {settings.storage_root}")


async def on_shutdown() -> None:
    """Shutdown actions."""
    logger.info("Bot stopped")


async def verify_fsm_storage() -> None:
    """Ping RedisStorage at startup; on failure, swap Dispatcher to MemoryStorage.

    Keeps the bot alive when Redis is unreachable — FSM state becomes volatile,
    but polling and handlers continue to work.
    """
    if not isinstance(dp.fsm.storage, RedisStorage):
        return
    try:
        await dp.fsm.storage.redis.ping()
        logger.info("Redis FSM storage ping OK")
    except Exception as exc:
        logger.warning(
            "Redis FSM storage unreachable ({}); falling back to MemoryStorage",
            exc,
        )
        with contextlib.suppress(Exception):
            await dp.fsm.storage.close()
        dp.fsm.storage = MemoryStorage()


async def main() -> None:
    """Main function."""
    # Setup logging
    setup_logging(settings.log_level)

    # Verify FSM storage is reachable; fallback to memory if Redis is down.
    await verify_fsm_storage()

    # Initialize database
    db = Database(settings.db_path)
    await db.connect()

    # Initialize storage service
    storage = StorageService(settings.storage_root)

    # Set bot commands
    await set_commands(bot)

    # Register middlewares (ORDER MATTERS!)
    # 1. Logging - first to log all events
    dp.message.middleware(LoggingMiddleware())
    dp.callback_query.middleware(LoggingMiddleware())

    # 2. Throttling - second to prevent flood
    # Separate instances so message and callback cooldowns are independent.
    dp.message.middleware(ThrottlingMiddleware(rate_limit=1.0))
    dp.callback_query.middleware(ThrottlingMiddleware(rate_limit=1.0))

    # 3. Database - last to inject repositories after throttling
    dp.message.middleware(DatabaseMiddleware(db))
    dp.callback_query.middleware(DatabaseMiddleware(db))

    # Inject storage service into dispatcher data
    dp["storage_service"] = storage

    # Include routers (ORDER MATTERS!)
    dp.include_routers(
        common.router,  # /start, /cancel, language
        download.router,  # Protocol downloads
        user.filters.router,  # Filter-based search
        user.search.router,  # Text search
        user.documents.router,  # Additional documents
        admin.upload_document.router,  # Document upload (BEFORE upload!)
        admin.upload.router,  # Protocol upload
        admin.moderators.router,  # Moderator management
    )

    # Register startup/shutdown hooks
    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)

    # Start polling
    logger.info("Starting bot polling...")
    try:
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.exception(f"Bot crashed: {e}")
        sys.exit(1)
    finally:
        await bot.session.close()
        await db.close()
        with contextlib.suppress(Exception):
            await dp.fsm.storage.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user (KeyboardInterrupt)")
