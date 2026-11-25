import asyncio
import logging

import db
from config import ADMIN_CHAT_ID, BOT_TOKEN, CHANNEL_LINK, MINI_APP_URL, PORT
from bot import bot, dp  # いмпортируем бота и диспетчер с уже зарегистрированными хендлерами
from web_server import start_web_server
from fastapi_app import app as fastapi_app
import uvicorn

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


async def run_bot() -> None:
    """Запускает бота в режиме long polling."""
    await db.init_db()
    await set_bot_commands()
    logger.info("Bot commands set")
    await dp.start_polling(bot)


async def set_bot_commands() -> None:
    """Настройка команд меню бота."""
    from aiogram.types import BotCommand

    commands = [
        BotCommand(command="start", description="👋 Главное меню"),
        BotCommand(command="suggest", description="📝 Отправить предложение"),
        BotCommand(command="contact", description="💬 Связаться с админами"),
        BotCommand(command="stats", description="📊 Статистика и рейтинг"),
    ]
    await bot.set_my_commands(commands)


async def run_fastapi() -> None:
    """Запускает FastAPI сервер на порту PORT + 1."""
    config = uvicorn.Config(
        fastapi_app,
        host="0.0.0.0",
        port=PORT + 1,
        log_level="info",
    )
    server = uvicorn.Server(config)
    await server.serve()


async def main() -> None:
    """Запускает бота, health-check и FastAPI параллельно."""
    web_runner = await start_web_server()

    await asyncio.gather(
        run_bot(),
        run_fastapi(),
    )

    await web_runner.cleanup()


if __name__ == "__main__":
    asyncio.run(main())