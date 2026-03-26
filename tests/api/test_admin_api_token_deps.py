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
    try:
        queue_admin.settings.ADMIN_API_TOKEN = ""
        queue_admin.settings.WEBHOOK_ADMIN_TOKEN = "legacy-token"
        client = TestClient(app)
        response = client.get("/api/queue/stats", headers={"X-Admin-Api-Token": "legacy-token"})
        # Router may fail later due to missing redis in test env, but should pass auth.
        assert response.status_code != 401
    finally:
        queue_admin.settings.ADMIN_API_TOKEN = original_admin
        queue_admin.settings.WEBHOOK_ADMIN_TOKEN = original_legacy
