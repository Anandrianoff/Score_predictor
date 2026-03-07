from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import Message
import logging
from logic_for_channel import daily_send
import os
from dotenv import load_dotenv

load_dotenv()
ADMIN = os.getenv('ADMIN')


logger = logging.getLogger(__name__)
router = Router()

@router.message(F.text)
async def all_messages(message: Message):
    await message.answer('Я не умею обшаться в личных чатах')

@router.message(Command('send_scores'))
async def send_scores(message: Message):
    if message.from_user.id == ADMIN:
        await daily_send()
        await message.answer('Успешно')


