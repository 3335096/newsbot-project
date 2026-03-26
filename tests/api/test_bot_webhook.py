from __future__ import annotations

import os

os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("TELEGRAM_BOT_TOKEN", "test-token")
os.environ.setdefault("TELEGRAM_WEBHOOK_SECRET", "secret-token")

from fastapi.testclient import TestClient

from app.main import app
from app.api.routers import bot_webhook as bot_webhook_router
from bot.runtime import WebhookInfo
from bot.runtime import WebhookInfo


bot_webhook_router.settings.TELEGRAM_WEBHOOK_SECRET = "secret-token"
bot_webhook_router.settings.TELEGRAM_WEBHOOK_URL = "https://example.com/bot/webhook"


def _minimal_update_payload() -> dict:
    return {
        "update_id": 123,
        "message": {
            "message_id": 1,
            "date": 1711360800,
            "chat": {"id": 1, "type": "private"},
            "from": {"id": 1, "is_bot": False, "first_name": "Test"},
            "text": "/start",
        },
    }


def test_webhook_rejects_invalid_secret() -> None:
    client = TestClient(app)
    response = client.post(
        "/bot/webhook",
        json=_minimal_update_payload(),
        headers={"X-Telegram-Bot-Api-Secret-Token": "wrong"},
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid webhook secret"


def test_webhook_accepts_valid_secret_and_feeds_dispatcher() -> None:
    client = TestClient(app)

    class _DummyDispatcher:
        def __init__(self) -> None:
            self.called = False

        async def feed_update(self, bot, update) -> None:
            self.called = True
            assert update.update_id == 123

    dummy = _DummyDispatcher()
    original_get_dispatcher = bot_webhook_router.get_dispatcher
    original_get_bot = bot_webhook_router.get_bot
    try:
        bot_webhook_router.get_dispatcher = lambda: dummy
        bot_webhook_router.get_bot = lambda: None
        response = client.post(
            "/bot/webhook",
            json=_minimal_update_payload(),
            headers={"X-Telegram-Bot-Api-Secret-Token": "secret-token"},
        )
        assert response.status_code == 200
        assert response.json()["status"] == "ok"
        assert dummy.called is True
    finally:
        bot_webhook_router.get_dispatcher = original_get_dispatcher
        bot_webhook_router.get_bot = original_get_bot


def test_webhook_info_endpoint_returns_runtime_info() -> None:
    client = TestClient(app)

    original_get_webhook_info = bot_webhook_router.get_webhook_info
    try:
        async def _fake_get_webhook_info():
            return WebhookInfo(
                url="https://example.com/bot/webhook",
                has_custom_certificate=False,
                pending_update_count=2,
                ip_address=None,
                last_error_date=None,
                last_error_message=None,
                max_connections=40,
                allowed_updates=["message", "callback_query"],
            )

        bot_webhook_router.get_webhook_info = _fake_get_webhook_info
        response = client.get("/bot/webhook/info")
        assert response.status_code == 200
        payload = response.json()
        assert payload["url"] == "https://example.com/bot/webhook"
        assert payload["pending_update_count"] == 2
    finally:
        bot_webhook_router.get_webhook_info = original_get_webhook_info


def test_webhook_set_uses_payload_values() -> None:
    client = TestClient(app)
    calls: dict[str, object] = {}
    original_set_webhook = bot_webhook_router.set_webhook
    original_delete_webhook = bot_webhook_router.delete_webhook
    try:
        async def _fake_set_webhook(url: str, secret_token: str | None = None) -> bool:
            calls["url"] = url
            calls["secret_token"] = secret_token
            return True

        async def _fake_delete_webhook(drop_pending_updates: bool = False) -> bool:
            calls["drop_pending_updates"] = drop_pending_updates
            return True

        bot_webhook_router.set_webhook = _fake_set_webhook
        bot_webhook_router.delete_webhook = _fake_delete_webhook

        response = client.post(
            "/bot/webhook/set",
            json={
                "url": "https://example.org/hook",
                "secret_token": "my-secret",
                "drop_pending_updates": True,
            },
        )
        assert response.status_code == 200
        payload = response.json()
        assert payload["status"] == "ok"
        assert payload["applied"] is True
        assert payload["url"] == "https://example.org/hook"
        assert calls["url"] == "https://example.org/hook"
        assert calls["secret_token"] == "my-secret"
        assert calls["drop_pending_updates"] is True
    finally:
        bot_webhook_router.set_webhook = original_set_webhook
        bot_webhook_router.delete_webhook = original_delete_webhook


def test_webhook_set_uses_config_url_when_payload_missing() -> None:
    client = TestClient(app)
    calls: dict[str, object] = {}
    original_set_webhook = bot_webhook_router.set_webhook
    try:
        async def _fake_set_webhook(url: str, secret_token: str | None = None) -> bool:
            calls["url"] = url
            calls["secret_token"] = secret_token
            return True

        bot_webhook_router.set_webhook = _fake_set_webhook
        response = client.post("/bot/webhook/set", json={})
        assert response.status_code == 200
        assert calls["url"] == "https://example.com/bot/webhook"
        assert calls["secret_token"] == "secret-token"
    finally:
        bot_webhook_router.set_webhook = original_set_webhook


def test_webhook_set_returns_400_when_url_missing() -> None:
    client = TestClient(app)
    original_url = bot_webhook_router.settings.TELEGRAM_WEBHOOK_URL
    bot_webhook_router.settings.TELEGRAM_WEBHOOK_URL = ""
    try:
        response = client.post("/bot/webhook/set", json={})
        assert response.status_code == 400
        assert response.json()["detail"] == "Webhook URL is required"
    finally:
        bot_webhook_router.settings.TELEGRAM_WEBHOOK_URL = original_url


def test_webhook_delete_endpoint_calls_runtime() -> None:
    client = TestClient(app)
    calls: dict[str, object] = {}
    original_delete_webhook = bot_webhook_router.delete_webhook
    try:
        async def _fake_delete_webhook(drop_pending_updates: bool = False) -> bool:
            calls["drop_pending_updates"] = drop_pending_updates
            return True

        bot_webhook_router.delete_webhook = _fake_delete_webhook
        response = client.post("/bot/webhook/delete?drop_pending_updates=true")
        assert response.status_code == 200
        payload = response.json()
        assert payload["status"] == "ok"
        assert payload["applied"] is True
        assert calls["drop_pending_updates"] is True
    finally:
        bot_webhook_router.delete_webhook = original_delete_webhook
