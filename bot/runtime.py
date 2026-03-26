from __future__ import annotations

from aiogram import Bot, Dispatcher
from aiogram.types import BotCommand

from bot.handlers import admin, drafts, ops, settings as settings_handler, sources, start
from core.config import settings

_bot: Bot | None = None
_dispatcher: Dispatcher | None = None


def get_bot() -> Bot:
    global _bot
    if _bot is None:
        _bot = Bot(token=settings.TELEGRAM_BOT_TOKEN)
    return _bot


def get_dispatcher() -> Dispatcher:
    global _dispatcher
    if _dispatcher is None:
        dispatcher = Dispatcher()
        dispatcher.include_router(start.router)
        dispatcher.include_router(admin.router)
        dispatcher.include_router(drafts.router)
        dispatcher.include_router(sources.router)
        dispatcher.include_router(ops.router)
        dispatcher.include_router(settings_handler.router)
        _dispatcher = dispatcher
    return _dispatcher


async def close_bot_session() -> None:
    global _bot
    if _bot is None:
        return
    try:
        await _bot.session.close()
    finally:
        _bot = None


async def ensure_bot_commands() -> None:
    bot = get_bot()
    await bot.set_my_commands(
        [
            BotCommand(command="start", description="Открыть главное меню"),
            BotCommand(command="admin", description="Админ-панель"),
            BotCommand(command="requeue_failed", description="Requeue failed job по id"),
        ]
    )

