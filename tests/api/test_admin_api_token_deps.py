from __future__ import annotations

import os

os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("TELEGRAM_BOT_TOKEN", "test-token")
os.environ.setdefault("ADMIN_API_TOKEN", "admin-token")

from fastapi.testclient import TestClient

from app.api import deps as api_deps
from app.main import app
from app.api.routers import llm, moderation, queue_admin


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


def test_admin_api_token_is_required_when_configured() -> None:
    original_admin = queue_admin.settings.ADMIN_API_TOKEN
    try:
        queue_admin.settings.ADMIN_API_TOKEN = "required-token"
        client = TestClient(app)
        response = client.get("/api/queue/stats")
        assert response.status_code == 401
        assert response.json()["detail"] == "Invalid admin api token"
    finally:
        queue_admin.settings.ADMIN_API_TOKEN = original_admin


def test_admin_api_rate_limit_kicks_in_on_repeated_failures() -> None:
    original_admin = api_deps.settings.ADMIN_API_TOKEN
    original_limit = api_deps.settings.ADMIN_API_RATE_LIMIT_COUNT
    original_window = api_deps.settings.ADMIN_API_RATE_LIMIT_WINDOW_SECONDS
    original_failures = dict(api_deps._admin_token_failures)
    try:
        api_deps._admin_token_failures.clear()
        api_deps.settings.ADMIN_API_TOKEN = "expected"
        api_deps.settings.ADMIN_API_RATE_LIMIT_COUNT = 2
        api_deps.settings.ADMIN_API_RATE_LIMIT_WINDOW_SECONDS = 60
        client = TestClient(app)

        r1 = client.get("/api/queue/stats", headers={"X-Admin-Api-Token": "bad"})
        r2 = client.get("/api/queue/stats", headers={"X-Admin-Api-Token": "bad"})
        r3 = client.get("/api/queue/stats", headers={"X-Admin-Api-Token": "bad"})

        assert r1.status_code == 401
        assert r2.status_code == 401
        assert r3.status_code == 429
        assert r3.json()["detail"] == "Too many invalid admin token attempts"
    finally:
        api_deps.settings.ADMIN_API_TOKEN = original_admin
        api_deps.settings.ADMIN_API_RATE_LIMIT_COUNT = original_limit
        api_deps.settings.ADMIN_API_RATE_LIMIT_WINDOW_SECONDS = original_window
        api_deps._admin_token_failures.clear()
        api_deps._admin_token_failures.update(original_failures)


def test_admin_api_rate_limit_key_masks_token_length() -> None:
    assert api_deps._rate_limit_key(None) == "<missing>"
    assert api_deps._rate_limit_key("abc") == "<len=3>"
