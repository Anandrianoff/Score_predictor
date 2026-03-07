from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import Message
import logging
from logic_for_channel import daily_send
import os
import sys
from dotenv import load_dotenv
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
root = os.path.dirname(parent_dir)
utils_dir = os.path.join(parent_dir, 'Utils')
sys.path.append(utils_dir)

from background_score_predictor import update_prediction

load_dotenv()
ADMIN = os.getenv('ADMIN')


logger = logging.getLogger(__name__)
router = Router()

@router.message(Command('send_scores'))
async def send_scores(message: Message):
    if message.from_user.id == int(ADMIN):
        await daily_send()
        await message.answer('Успешно')
    else:
        await message.answer('С новым годом, пошёл нафиг')

@router.message(Command('update_predictions'))
async def send_scores(message: Message):
    if message.from_user.id == int(ADMIN):
        update_prediction()
        await message.answer('Успешно')
    else:
        await message.answer('С новым годом, пошёл нафиг')
