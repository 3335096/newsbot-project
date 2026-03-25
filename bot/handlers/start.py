from aiogram import Router, types
from aiogram.filters import CommandStart
from bot.keyboards.main_menu import main_menu_kb

router = Router()

@router.message(CommandStart())
async def command_start_handler(message: types.Message) -> None:
    await message.answer(f"Hello, {message.from_user.full_name}!\nThis is NewsBot. How can I help you?", reply_markup=main_menu_kb)
