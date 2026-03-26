from __future__ import annotations

import os

os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("TELEGRAM_BOT_TOKEN", "test-token")
os.environ.setdefault("ADMIN_API_TOKEN", "admin-token")

from fastapi.testclient import TestClient

from app.main import app
from app.api.routers import queue_admin, llm, moderation


def test_queue_stats_requires_admin_api_token() -> None:
    client = TestClient(app)
    response = client.get("/api/queue/stats", headers={"X-Admin-Api-Token": "wrong"})
    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid admin api token"


def test_moderation_rules_requires_admin_api_token() -> None:
    client = TestClient(app)
    response = client.get("/api/moderation/rules", headers={"X-Admin-Api-Token": "wrong"})
    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid admin api token"


def test_llm_preset_update_requires_admin_api_token() -> None:
    client = TestClient(app)
    response = client.post(
        "/api/llm/presets/summary",
        json={"enabled": True},
        headers={"X-Admin-Api-Token": "wrong"},
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid admin api token"


def test_admin_api_token_fallback_to_legacy_webhook_token() -> None:
    original_admin = queue_admin.settings.ADMIN_API_TOKEN
    original_legacy = queue_admin.settings.WEBHOOK_ADMIN_TOKEN
    original_queue_snapshot = queue_admin.queue_snapshot
    original_get_redis_connection = queue_admin.get_redis_connection
    original_get_worker_last_seen = queue_admin.get_worker_last_seen
    original_is_worker_alive = queue_admin.is_worker_alive
    try:
        queue_admin.settings.ADMIN_API_TOKEN = ""
        queue_admin.settings.WEBHOOK_ADMIN_TOKEN = "legacy-token"
        queue_admin.queue_snapshot = lambda name: queue_admin.QueueStatsOut(  # type: ignore[assignment]
            name=name,
            queued=0,
            started=0,
            finished=0,
            failed=0,
            deferred=0,
            scheduled=0,
        )
        queue_admin.get_redis_connection = lambda: type(  # type: ignore[assignment]
            "_FakeRedis",
            (),
            {"ping": staticmethod(lambda: True)},
        )()
        queue_admin.get_worker_last_seen = lambda: None  # type: ignore[assignment]
        queue_admin.is_worker_alive = lambda: False  # type: ignore[assignment]
        client = TestClient(app)
        response = client.get("/api/queue/stats", headers={"X-Admin-Api-Token": "legacy-token"})
        assert response.status_code == 200
    finally:
        queue_admin.settings.ADMIN_API_TOKEN = original_admin
        queue_admin.settings.WEBHOOK_ADMIN_TOKEN = original_legacy
        queue_admin.queue_snapshot = original_queue_snapshot
        queue_admin.get_redis_connection = original_get_redis_connection
        queue_admin.get_worker_last_seen = original_get_worker_last_seen
        queue_admin.is_worker_alive = original_is_worker_alive
