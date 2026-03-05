from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import Message, FSInputFile
from aiogram.fsm.context import FSMContext
import logging


logger = logging.getLogger(__name__)
router = Router()

@router.message(F.text)
async def all_messages(message: Message):
    await message.answer('Я не умею обшаться в личных чатах')


