import logging
import os
import sys
from pathlib import Path

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import Message
from dotenv import load_dotenv

_root = Path(__file__).resolve().parents[2]
_src = _root / "src"
if str(_src) not in sys.path:
    sys.path.insert(0, str(_src))

from score_predictor.bootstrap import ensure_project_import_paths

ensure_project_import_paths()

from background_score_predictor import update_prediction
from logic_for_channel import (
    daily_send,
    make_bets_for_day,
    update_yesterday_bet_results,
    weekly_send,
    send_start_message,
)
from bacground_worker import update_games_info

load_dotenv()
ADMIN = os.getenv("ADMIN")

logger = logging.getLogger(__name__)
router = Router()


@router.message(Command("send_scores"))
async def send_scores(message: Message):
    if message.from_user.id == int(ADMIN):
        try:
            await daily_send()
            await message.answer("Успешно")
        except Exception as e:
            logger.error(f"Error in daily_send: {e}")
            await message.answer(f"Произошла ошибка при отправке результатов.\nОшибка: {e}")
    else:
        await message.answer("С новым годом, пошёл нафиг")


@router.message(Command("update_predictions"))
async def send_scores_update_prediction(message: Message):
    logger.info(f"Received update_prediction command from user {message.from_user.id}")
    if message.from_user.id == int(ADMIN):
        try:
            update_prediction()
            await message.answer("Успешно")
        except Exception as e:
            logger.error(f"Error in update_prediction: {e}")
            await message.answer(f"Произошла ошибка при обновлении предсказаний.\nОшибка: {e}")
    else:
        await message.answer("С новым годом, пошёл нафиг")

@router.message(Command("update_all"))
async def send_scores_update_prediction(message: Message):
    logger.info(f"Received update_all command from user {message.from_user.id}")
    if message.from_user.id == int(ADMIN):
        try:
            update_games_info()
            update_yesterday_bet_results()
            await message.answer("Успешно")
        except Exception as e:
            logger.error(f"Error in update_prediction: {e}")
            await message.answer(f"Произошла ошибка при update_all.\nОшибка: {e}")
    else:
        await message.answer("С новым годом, пошёл нафиг")