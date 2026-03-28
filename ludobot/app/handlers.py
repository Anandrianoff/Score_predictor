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
from logic_for_channel import daily_send

load_dotenv()
ADMIN = os.getenv("ADMIN")

logger = logging.getLogger(__name__)
router = Router()


@router.message(Command("send_scores"))
async def send_scores(message: Message):
    if message.from_user.id == int(ADMIN):
        await daily_send()
        await message.answer("Успешно")
    else:
        await message.answer("С новым годом, пошёл нафиг")


@router.message(Command("update_prediction"))
async def send_scores_update_prediction(message: Message):
    if message.from_user.id == int(ADMIN):
        update_prediction()
        await message.answer("Успешно")
    else:
        await message.answer("С новым годом, пошёл нафиг")
