from __future__ import annotations

import time
from collections import defaultdict, deque

from fastapi import Header, HTTPException
from loguru import logger

from core.config import settings

_admin_token_failures: defaultdict[str, deque[float]] = defaultdict(deque)


def _rate_limit_key(token: str | None) -> str:
    if not token:
        return "<missing>"
    return f"<len={len(token)}>"


def _enforce_admin_rate_limit(token: str | None) -> None:
    limit = max(int(settings.ADMIN_API_RATE_LIMIT_COUNT), 1)
    window = max(int(settings.ADMIN_API_RATE_LIMIT_WINDOW_SECONDS), 1)
    now = time.time()
    key = _rate_limit_key(token)
    bucket = _admin_token_failures[key]
    while bucket and (now - bucket[0]) > window:
        bucket.popleft()
    bucket.append(now)
    if len(bucket) > limit:
        raise HTTPException(status_code=429, detail="Too many invalid admin token attempts")


def _audit_invalid_admin_token(token: str | None) -> None:
    if settings.ADMIN_API_AUDIT_LOG_ENABLED:
        logger.warning("Admin API token validation failed (token={})", _rate_limit_key(token))


def require_admin_api_token(x_admin_api_token: str | None = Header(default=None)) -> None:
    expected = settings.ADMIN_API_TOKEN.strip()
    if not expected:
        return
    if x_admin_api_token != expected:
        _audit_invalid_admin_token(x_admin_api_token)
        _enforce_admin_rate_limit(x_admin_api_token)
        raise HTTPException(status_code=401, detail="Invalid admin api token")
