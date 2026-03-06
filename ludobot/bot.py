import sys
import os

current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sister_dir = os.path.join(current_dir, 'app')
sys.path.append(sister_dir)

import asyncio
import logging
from logging.handlers import RotatingFileHandler
from create_bot import dp, bot
from handlers import router
from logic_for_channel import daily_send
from apscheduler.schedulers.asyncio import AsyncIOScheduler


scheduler = AsyncIOScheduler()

async def main():
    scheduler.add_job(daily_send, 'cron', hour = 11, minute = 30)
    dp.include_router(router)
    await dp.start_polling(bot)


if __name__ == "__main__":
    handler = RotatingFileHandler("ludobot.log", maxBytes=1_000_000, backupCount=6)

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