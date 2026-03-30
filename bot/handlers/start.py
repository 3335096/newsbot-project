from aiogram import Router, types
from aiogram.filters import CommandStart
from bot.keyboards.main_menu import build_main_menu_kb
from core.config import settings

router = Router()

@router.message(CommandStart())
async def command_start_handler(message: types.Message) -> None:
    user_id = message.from_user.id
    if user_id not in settings.allowed_user_ids:
        await message.answer("Доступ запрещен. Обратитесь к администратору.")
        return

    await message.answer(
        f"Привет, {message.from_user.full_name}!\n"
        "Это NewsBot. Выберите действие в меню ниже.",
        reply_markup=build_main_menu_kb(),
    )
