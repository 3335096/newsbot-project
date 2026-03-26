from __future__ import annotations

import hashlib
import time
from collections import defaultdict, deque

from fastapi import Header, HTTPException
from loguru import logger

from app.queue import get_redis_connection
from core.config import settings

_admin_token_failures: defaultdict[str, deque[float]] = defaultdict(deque)


def _rate_limit_key(token: str | None) -> str:
    if not token:
        return "<missing>"
    return f"<len={len(token)}>"


def _redis_rate_limit_key(token: str | None) -> str:
    raw = token or "<missing>"
    digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()
    prefix = settings.ADMIN_API_RATE_LIMIT_REDIS_PREFIX.strip() or "newsbot:admin_auth:failures"
    return f"{prefix}:{digest}"


def _enforce_admin_rate_limit_redis(token: str | None) -> bool:
    limit = max(int(settings.ADMIN_API_RATE_LIMIT_COUNT), 1)
    window = max(int(settings.ADMIN_API_RATE_LIMIT_WINDOW_SECONDS), 1)
    key = _redis_rate_limit_key(token)
    redis = get_redis_connection()
    current = redis.incr(key)
    if current == 1:
        redis.expire(key, window)
    return int(current) > limit


def _enforce_admin_rate_limit(token: str | None) -> None:
    try:
        if _enforce_admin_rate_limit_redis(token):
            raise HTTPException(status_code=429, detail="Too many invalid admin token attempts")
        return
    except HTTPException:
        raise
    except Exception as exc:
        if not settings.ADMIN_API_RATE_LIMIT_ALLOW_INMEMORY_FALLBACK:
            logger.warning("Admin rate-limit redis failed and fallback disabled: {}", exc)
            return
        logger.warning("Admin rate-limit redis failed, using in-memory fallback: {}", exc)

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
