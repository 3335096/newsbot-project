from __future__ import annotations

import os

os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("TELEGRAM_BOT_TOKEN", "test-token")
os.environ.setdefault("TELEGRAM_WEBHOOK_SECRET", "secret-token")

from fastapi.testclient import TestClient

from app.main import app
from app.api.routers import bot_webhook as bot_webhook_router


bot_webhook_router.settings.TELEGRAM_WEBHOOK_SECRET = "secret-token"


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
