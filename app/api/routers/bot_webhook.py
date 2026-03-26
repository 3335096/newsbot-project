from __future__ import annotations

from fastapi import APIRouter, Header, HTTPException, Request
from pydantic import BaseModel
from aiogram.types import Update

from bot.runtime import (
    delete_webhook,
    get_bot,
    get_dispatcher,
    get_webhook_info,
    set_webhook,
)
from core.config import settings

router = APIRouter(prefix="/bot", tags=["bot"])


class WebhookSetPayload(BaseModel):
    url: str | None = None
    secret_token: str | None = None
    drop_pending_updates: bool = False


class WebhookOperationOut(BaseModel):
    status: str
    applied: bool
    url: str | None = None


def _require_webhook_admin_token(x_webhook_admin_token: str | None) -> None:
    expected = settings.WEBHOOK_ADMIN_TOKEN.strip()
    if not expected:
        return
    if x_webhook_admin_token != expected:
        raise HTTPException(status_code=401, detail="Invalid webhook admin token")


@router.post("/webhook")
async def bot_webhook(
    request: Request,
    x_telegram_bot_api_secret_token: str | None = Header(default=None),
) -> dict[str, str]:
    expected_secret = settings.TELEGRAM_WEBHOOK_SECRET.strip()
    if expected_secret:
        if x_telegram_bot_api_secret_token != expected_secret:
            raise HTTPException(status_code=401, detail="Invalid webhook secret")

    payload = await request.json()
    update = Update.model_validate(payload)
    bot = get_bot()
    dp = get_dispatcher()
    await dp.feed_update(bot, update)
    return {"status": "ok"}


@router.get("/webhook/info")
async def bot_webhook_info(x_webhook_admin_token: str | None = Header(default=None)):
    _require_webhook_admin_token(x_webhook_admin_token)
    info = await get_webhook_info()
    return info.model_dump()


@router.post("/webhook/set", response_model=WebhookOperationOut)
async def bot_webhook_set(
    payload: WebhookSetPayload,
    x_webhook_admin_token: str | None = Header(default=None),
):
    _require_webhook_admin_token(x_webhook_admin_token)
    url = (payload.url or settings.TELEGRAM_WEBHOOK_URL).strip()
    if not url:
        raise HTTPException(status_code=400, detail="Webhook URL is required")

    secret_token = payload.secret_token
    if secret_token is None:
        configured_secret = settings.TELEGRAM_WEBHOOK_SECRET.strip()
        secret_token = configured_secret or None

    if payload.drop_pending_updates:
        await delete_webhook(drop_pending_updates=True)
    applied = await set_webhook(url=url, secret_token=secret_token)
    return WebhookOperationOut(status="ok", applied=bool(applied), url=url)


@router.post("/webhook/delete", response_model=WebhookOperationOut)
async def bot_webhook_delete(
    drop_pending_updates: bool = False,
    x_webhook_admin_token: str | None = Header(default=None),
):
    _require_webhook_admin_token(x_webhook_admin_token)
    applied = await delete_webhook(drop_pending_updates=drop_pending_updates)
    return WebhookOperationOut(status="ok", applied=bool(applied), url=None)
