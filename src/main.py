import asyncio
import logging
import sys
import uvicorn
from src.api.app import app
from src.bot.bot import create_bot, create_dispatcher
from src.config import settings
from src.database.session import init_db

logging.basicConfig(
    level=logging.INFO if settings.DEBUG else logging.WARNING,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("musicbot")


async def run_api():
    """Запуск FastAPI сервера через uvicorn."""
    config = uvicorn.Config(
        app=app,
        host=settings.API_HOST,
        port=settings.API_PORT,
        log_level="info" if settings.DEBUG else "warning",
    )
    server = uvicorn.Server(config)
    logger.info(f"🚀 Запуск FastAPI API на http://{settings.API_HOST}:{settings.API_PORT}")
    await server.serve()


async def run_bot():
    """Запуск Telegram бота через aiogram polling."""
    if settings.BOT_TOKEN in ("MOCK_TOKEN", "", "change_me"):
        logger.warning(
            "⚠️ BOT_TOKEN не задан в .env! Поллинг бота отключен. Запущен только WebApp API сервер."
        )
        # Заглушка ожидания, пока работает API
        while True:
            await asyncio.sleep(3600)

    bot = create_bot()
    dp = create_dispatcher()
    logger.info("🤖 Запуск Telegram Bot polling...")
    try:
        from aiogram.types import MenuButtonWebApp, WebAppInfo
        await bot.set_chat_menu_button(
            menu_button=MenuButtonWebApp(
                text="🎵 Плеер",
                web_app=WebAppInfo(url=settings.WEBAPP_URL),
            )
        )
        logger.info(f"✅ Установлена кнопка меню WebApp: {settings.WEBAPP_URL}")
    except Exception as e:
        logger.warning(f"Не удалось настроить кнопку меню бота: {e}")

    try:
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    finally:
        await bot.session.close()


async def main():
    """Точка входа: инициализация БД и запуск Bot + API."""
    logger.info("📦 Инициализация базы данных...")
    await init_db()
    logger.info("✅ База данных готова.")

    await asyncio.gather(
        run_api(),
        run_bot(),
    )


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("🛑 Сервис остановлен.")
