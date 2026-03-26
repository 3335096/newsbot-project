from __future__ import annotations

from aiogram import Bot, Dispatcher
from aiogram.types import BotCommand
from pydantic import BaseModel

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


class WebhookInfo(BaseModel):
    url: str
    has_custom_certificate: bool
    pending_update_count: int
    ip_address: str | None = None
    last_error_date: int | None = None
    last_error_message: str | None = None
    max_connections: int | None = None
    allowed_updates: list[str] | None = None


async def get_webhook_info() -> WebhookInfo:
    bot = get_bot()
    info = await bot.get_webhook_info()
    return WebhookInfo(
        url=info.url,
        has_custom_certificate=info.has_custom_certificate,
        pending_update_count=info.pending_update_count,
        ip_address=info.ip_address,
        last_error_date=info.last_error_date,
        last_error_message=info.last_error_message,
        max_connections=info.max_connections,
        allowed_updates=info.allowed_updates,
    )


async def set_webhook(url: str, secret_token: str | None = None) -> bool:
    bot = get_bot()
    return await bot.set_webhook(url=url, secret_token=secret_token)


async def delete_webhook(drop_pending_updates: bool = False) -> bool:
    bot = get_bot()
    return await bot.delete_webhook(drop_pending_updates=drop_pending_updates)

