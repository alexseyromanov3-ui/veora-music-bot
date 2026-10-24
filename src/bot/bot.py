from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from src.bot.handlers import common, search, upload
from src.config import settings


def create_bot() -> Bot:
    """Инициализация экземпляра бота aiogram."""
    return Bot(
        token=settings.BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )


def create_dispatcher() -> Dispatcher:
    """Инициализация диспетчера и регистрация роутеров."""
    dp = Dispatcher()
    dp.include_router(common.router)
    dp.include_router(upload.router)
    dp.include_router(search.router)
    return dp
