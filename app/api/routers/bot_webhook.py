from __future__ import annotations

from fastapi import APIRouter, Header, HTTPException, Request
from aiogram.types import Update

from bot.runtime import get_bot, get_dispatcher
from core.config import settings

router = APIRouter(prefix="/bot", tags=["bot"])


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
