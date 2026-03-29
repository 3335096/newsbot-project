from __future__ import annotations

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from pydantic import BaseModel
from aiogram.types import Update
from loguru import logger

from app.api.deps import require_admin_api_token
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


@router.post("/webhook")
async def bot_webhook(
    request: Request,
    x_telegram_bot_api_secret_token: str | None = Header(default=None),
) -> dict[str, str]:
    expected_secret = settings.TELEGRAM_WEBHOOK_SECRET.strip()
    if expected_secret:
        if x_telegram_bot_api_secret_token != expected_secret:
            raise HTTPException(status_code=401, detail="Invalid webhook secret")

    try:
        payload = await request.json()
        update = Update.model_validate(payload)
    except Exception as exc:
        logger.exception("Failed to parse Telegram webhook update: {}", exc)
        # Always return 200 for malformed updates to avoid endless Telegram retries.
        return {"status": "ignored"}

    try:
        bot = get_bot()
        dp = get_dispatcher()
        await dp.feed_update(bot, update)
    except Exception as exc:
        logger.exception("Failed to process Telegram webhook update: {}", exc)
        # Return 200 and log the root cause; Telegram retries can otherwise amplify failures.
        return {"status": "failed"}

    return {"status": "ok"}


@router.get("/webhook/info")
async def bot_webhook_info(
    _: None = Depends(require_admin_api_token),
):
    info = await get_webhook_info()
    return info.model_dump()


@router.post("/webhook/set", response_model=WebhookOperationOut)
async def bot_webhook_set(
    payload: WebhookSetPayload,
    _: None = Depends(require_admin_api_token),
):
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
    _: None = Depends(require_admin_api_token),
):
    applied = await delete_webhook(drop_pending_updates=drop_pending_updates)
    return WebhookOperationOut(status="ok", applied=bool(applied), url=None)
