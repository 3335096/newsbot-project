import asyncio
import logging

from aiogram import Bot, Dispatcher
from core.config import settings
from bot.handlers import start, admin, drafts

async def main():
    logging.basicConfig(level=logging.INFO)

    bot = Bot(token=settings.TELEGRAM_BOT_TOKEN)
    dp = Dispatcher()

    dp.include_router(start.router)
    dp.include_router(admin.router)
    dp.include_router(drafts.router)

    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
