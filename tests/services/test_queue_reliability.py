from __future__ import annotations

import asyncio
import os
import time

os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("TELEGRAM_BOT_TOKEN", "test-token")

from app.services import worker_state
from app.services.worker_state import WORKER_HEARTBEAT_KEY, heartbeat_worker, is_worker_alive
from app.api.routers import queue_admin
from app import queue as queue_module


class _FakeRedis:
    def __init__(self) -> None:
        self.storage: dict[str, object] = {}

    def set(self, key: str, value: object, ex: int | None = None) -> None:
        self.storage[key] = value

    def get(self, key: str):
        return self.storage.get(key)

    def ping(self) -> bool:
        return True


def test_worker_heartbeat_sets_timestamp_in_redis() -> None:
    fake = _FakeRedis()
    original_get_conn = queue_module.get_redis_connection
    original_get_conn_worker = worker_state.get_redis_connection
    try:
        queue_module.get_redis_connection = lambda: fake
        worker_state.get_redis_connection = lambda: fake
        ts = heartbeat_worker()
        assert isinstance(ts, int)
        assert fake.get(WORKER_HEARTBEAT_KEY) == ts
    finally:
        queue_module.get_redis_connection = original_get_conn
        worker_state.get_redis_connection = original_get_conn_worker


def test_queue_admin_reports_worker_alive_from_recent_heartbeat() -> None:
    fake = _FakeRedis()
    now_ts = int(time.time())
    fake.set(WORKER_HEARTBEAT_KEY, now_ts)

    original_queue_snapshot = queue_admin.queue_snapshot
    original_get_conn_queue = queue_module.get_redis_connection
    original_get_conn_router = queue_admin.get_redis_connection
    original_get_conn_worker = worker_state.get_redis_connection
    try:
        queue_module.get_redis_connection = lambda: fake
        queue_admin.get_redis_connection = lambda: fake
        worker_state.get_redis_connection = lambda: fake
        queue_admin.queue_snapshot = lambda name: queue_module.QueueSnapshot(  # type: ignore[assignment]
            name=name,
            queued=1,
            started=0,
            finished=0,
            failed=0,
            deferred=0,
            scheduled=0,
        )
        payload = asyncio.run(queue_admin.get_queue_stats())
        assert payload.redis_ok is True
        assert payload.worker_alive is True
    finally:
        queue_admin.queue_snapshot = original_queue_snapshot
        queue_module.get_redis_connection = original_get_conn_queue
        queue_admin.get_redis_connection = original_get_conn_router
        worker_state.get_redis_connection = original_get_conn_worker


def test_worker_alive_false_without_heartbeat() -> None:
    fake = _FakeRedis()
    original_get_conn = queue_module.get_redis_connection
    original_get_conn_worker = worker_state.get_redis_connection
    try:
        queue_module.get_redis_connection = lambda: fake
        worker_state.get_redis_connection = lambda: fake
        assert is_worker_alive() is False
    finally:
        queue_module.get_redis_connection = original_get_conn
        worker_state.get_redis_connection = original_get_conn_worker
