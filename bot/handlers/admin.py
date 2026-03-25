from aiogram import Router, types, F
from aiogram.filters import Command
from core.config import settings

router = Router()

@router.message(Command("admin"), F.from_user.id.in_(settings.admin_ids))
async def admin_panel(message: types.Message):
    await message.answer("Welcome to the admin panel!")

# More admin functionalities will be added here
