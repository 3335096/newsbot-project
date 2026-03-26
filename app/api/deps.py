from __future__ import annotations

from fastapi import Header, HTTPException

from core.config import settings


def require_admin_api_token(x_admin_api_token: str | None = Header(default=None)) -> None:
    expected = settings.ADMIN_API_TOKEN.strip() or settings.WEBHOOK_ADMIN_TOKEN.strip()
    if not expected:
        return
    if x_admin_api_token != expected:
        raise HTTPException(status_code=401, detail="Invalid admin api token")
