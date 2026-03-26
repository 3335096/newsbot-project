from __future__ import annotations

import time

from app.queue import get_redis_connection
from core.config import settings

WORKER_HEARTBEAT_KEY = "newsbot:worker:last_seen"


def heartbeat_worker() -> int:
    now_ts = int(time.time())
    redis = get_redis_connection()
    redis.set(WORKER_HEARTBEAT_KEY, now_ts, ex=settings.WORKER_HEARTBEAT_TTL_SECONDS * 3)
    return now_ts


def get_worker_last_seen() -> int | None:
    redis = get_redis_connection()
    value = redis.get(WORKER_HEARTBEAT_KEY)
    if value is None:
        return None
    try:
        return int(value)
    except Exception:
        return None


def is_worker_alive() -> bool:
    last_seen = get_worker_last_seen()
    if last_seen is None:
        return False
    age = int(time.time()) - last_seen
    return age <= settings.WORKER_HEARTBEAT_TTL_SECONDS
