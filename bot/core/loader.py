"""Bot and Dispatcher initialization."""

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.base import BaseStorage
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.storage.redis import RedisStorage
from loguru import logger

from bot.core.config import settings


def build_storage() -> BaseStorage:
    """Build FSM storage based on configuration.

    Uses RedisStorage when REDIS_URL is configured, otherwise falls back to
    MemoryStorage. Connection failures are handled at startup in __main__.

    Returns:
        Configured FSM storage instance.
    """
    if settings.redis_url:
        logger.info("FSM storage: Redis ({})", settings.redis_url)
        return RedisStorage.from_url(settings.redis_url)
    logger.warning("FSM storage: in-memory (state is lost on restart)")
    return MemoryStorage()


bot = Bot(
    token=settings.bot_token.get_secret_value(),
    default=DefaultBotProperties(parse_mode=ParseMode.HTML),
)

storage: BaseStorage = build_storage()
dp = Dispatcher(storage=storage)
