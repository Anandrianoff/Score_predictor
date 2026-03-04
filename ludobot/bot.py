import asyncio
import logging
from logging.handlers import RotatingFileHandler
from aiogram import Bot, Dispatcher
import os
from dotenv import load_dotenv
from handlers import handlers


async def main():
    load_dotenv()
    TOKEN = os.getenv('TOKEN')
    bot = Bot(token=TOKEN)
    dp = Dispatcher()
    dp.include_router(handlers)
    await dp.start_polling(bot)


if __name__ == "__main__":
    handler = RotatingFileHandler("app.log", maxBytes=1_000_000, backupCount=6)

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[handler],
    )
    logger = logging.getLogger(__name__)

    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.critical("Бот не смог стартовать")