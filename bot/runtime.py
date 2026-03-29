from __future__ import annotations

from datetime import datetime, timezone

from aiogram import Bot, Dispatcher
from aiogram.types import BotCommand
from pydantic import BaseModel, field_validator
from loguru import logger

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

    @field_validator("last_error_date", mode="before")
    @classmethod
    def _coerce_last_error_date(cls, value: object | None) -> int | None:
        return _normalize_telegram_timestamp(value)


def _normalize_telegram_timestamp(value: object | None) -> int | None:
    if value is None:
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if isinstance(value, datetime):
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return int(value.timestamp())
    try:
        return int(value)  # type: ignore[arg-type]
    except Exception:
        return None


async def get_webhook_info() -> WebhookInfo:
    bot = get_bot()
    info = await bot.get_webhook_info()
    return WebhookInfo(
        url=info.url,
        has_custom_certificate=info.has_custom_certificate,
        pending_update_count=info.pending_update_count,
        ip_address=info.ip_address,
        last_error_date=_normalize_telegram_timestamp(info.last_error_date),
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


async def sync_webhook_mode() -> dict[str, str]:
    if not settings.TELEGRAM_WEBHOOK_AUTOSYNC_ON_STARTUP:
        logger.info("Webhook autosync disabled by config")
        return {"action": "skipped", "reason": "autosync_disabled"}

    if settings.TELEGRAM_USE_WEBHOOK:
        url = settings.TELEGRAM_WEBHOOK_URL.strip()
        if not url:
            logger.warning(
                "Webhook mode enabled but TELEGRAM_WEBHOOK_URL is empty; skipping webhook set"
            )
            return {"action": "skipped", "reason": "missing_webhook_url"}
        current_info = await get_webhook_info()
        current_url = (current_info.url or "").strip()
        if (
            current_url == url
            and not settings.TELEGRAM_WEBHOOK_DROP_PENDING_ON_SET
        ):
            logger.info("Webhook already synchronized: {}", url)
            return {"action": "skipped", "reason": "already_set", "url": url}
        secret = settings.TELEGRAM_WEBHOOK_SECRET.strip() or None
        if settings.TELEGRAM_WEBHOOK_DROP_PENDING_ON_SET:
            await delete_webhook(drop_pending_updates=True)
        await set_webhook(url=url, secret_token=secret)
        logger.info("Webhook synchronized: set {}", url)
        return {"action": "set", "url": url}

    current_info = await get_webhook_info()
    if not (current_info.url or "").strip():
        logger.info("Webhook already absent; nothing to delete")
        return {"action": "skipped", "reason": "already_deleted"}
    await delete_webhook(
        drop_pending_updates=settings.TELEGRAM_WEBHOOK_DROP_PENDING_ON_DISABLE
    )
    logger.info(
        "Webhook synchronized: deleted (drop_pending_updates={})",
        settings.TELEGRAM_WEBHOOK_DROP_PENDING_ON_DISABLE,
    )
    return {"action": "deleted"}

