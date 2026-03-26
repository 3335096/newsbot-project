import asyncio
import logging

from bot.runtime import close_bot_session, ensure_bot_commands, get_bot, get_dispatcher

async def main():
    logging.basicConfig(level=logging.INFO)
    bot = get_bot()
    dp = get_dispatcher()
    await ensure_bot_commands()

    await bot.delete_webhook(drop_pending_updates=True)
    try:
        await dp.start_polling(bot)
    finally:
        await close_bot_session()

if __name__ == "__main__":
    asyncio.run(main())
