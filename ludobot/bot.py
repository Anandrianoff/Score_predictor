import sys
from pathlib import Path

_root = Path(__file__).resolve().parents[1]
_src = _root / "src"
if str(_src) not in sys.path:
    sys.path.insert(0, str(_src))

from score_predictor.bootstrap import ensure_project_import_paths

ensure_project_import_paths()

import asyncio
import logging
from logging.handlers import RotatingFileHandler

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from bacground_worker import update_games_info
from background_score_predictor import update_prediction
from create_bot import bot, dp
from handlers import router
from logic_for_channel import (
    daily_send,
    make_bets_for_day,
    update_yesterday_bet_results,
    weekly_send,
    send_start_message,
)
import ThresholdRFClassifier  # noqa: F401 — ensures ML Core import path works at startup

scheduler = AsyncIOScheduler()


async def main():
    await send_start_message()
    scheduler.add_job(update_games_info, "cron", hour=11, minute=22)
    scheduler.add_job(update_prediction, "cron", hour=11, minute=27)
    scheduler.add_job(make_bets_for_day, "cron", hour=11, minute=29)
    scheduler.add_job(update_yesterday_bet_results, "cron", hour=11, minute=29)
    scheduler.add_job(daily_send, "cron", hour=11, minute=30, jitter=20)
    scheduler.add_job(weekly_send, trigger="cron", day_of_week="tue", hour="11", minute="30")
    scheduler.start()

    dp.include_router(router)
    await dp.start_polling(bot)


if __name__ == "__main__":
    _log_fmt = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    file_handler = RotatingFileHandler("ludobot.log", maxBytes=1_000_000, backupCount=6)

    logging.basicConfig(
        level=logging.INFO,
        handlers=file_handler,
        format=_log_fmt,
    )
    logger = logging.getLogger(__name__)

    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.critical("Бот не смог стартовать")
