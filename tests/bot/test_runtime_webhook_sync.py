from __future__ import annotations

import asyncio
import os

os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("TELEGRAM_BOT_TOKEN", "test-token")

from bot import runtime


def test_sync_webhook_mode_skips_when_autosync_disabled() -> None:
    original_autosync = runtime.settings.TELEGRAM_WEBHOOK_AUTOSYNC_ON_STARTUP
    runtime.settings.TELEGRAM_WEBHOOK_AUTOSYNC_ON_STARTUP = False
    try:
        result = asyncio.run(runtime.sync_webhook_mode())
        assert result["action"] == "skipped"
        assert result["reason"] == "autosync_disabled"
    finally:
        runtime.settings.TELEGRAM_WEBHOOK_AUTOSYNC_ON_STARTUP = original_autosync


def test_sync_webhook_mode_sets_webhook_when_enabled() -> None:
    original_autosync = runtime.settings.TELEGRAM_WEBHOOK_AUTOSYNC_ON_STARTUP
    original_use_webhook = runtime.settings.TELEGRAM_USE_WEBHOOK
    original_url = runtime.settings.TELEGRAM_WEBHOOK_URL
    original_secret = runtime.settings.TELEGRAM_WEBHOOK_SECRET
    original_drop_on_set = runtime.settings.TELEGRAM_WEBHOOK_DROP_PENDING_ON_SET
    original_set_webhook = runtime.set_webhook
    original_delete_webhook = runtime.delete_webhook

    calls: dict[str, object] = {}
    try:
        runtime.settings.TELEGRAM_WEBHOOK_AUTOSYNC_ON_STARTUP = True
        runtime.settings.TELEGRAM_USE_WEBHOOK = True
        runtime.settings.TELEGRAM_WEBHOOK_URL = "https://example.com/bot/webhook"
        runtime.settings.TELEGRAM_WEBHOOK_SECRET = "secret-token"
        runtime.settings.TELEGRAM_WEBHOOK_DROP_PENDING_ON_SET = True

        async def _fake_delete_webhook(drop_pending_updates: bool = False) -> bool:
            calls["delete_drop"] = drop_pending_updates
            return True

        async def _fake_set_webhook(url: str, secret_token: str | None = None) -> bool:
            calls["url"] = url
            calls["secret_token"] = secret_token
            return True

        runtime.delete_webhook = _fake_delete_webhook
        runtime.set_webhook = _fake_set_webhook

        result = asyncio.run(runtime.sync_webhook_mode())
        assert result["action"] == "set"
        assert result["url"] == "https://example.com/bot/webhook"
        assert calls["delete_drop"] is True
        assert calls["url"] == "https://example.com/bot/webhook"
        assert calls["secret_token"] == "secret-token"
    finally:
        runtime.settings.TELEGRAM_WEBHOOK_AUTOSYNC_ON_STARTUP = original_autosync
        runtime.settings.TELEGRAM_USE_WEBHOOK = original_use_webhook
        runtime.settings.TELEGRAM_WEBHOOK_URL = original_url
        runtime.settings.TELEGRAM_WEBHOOK_SECRET = original_secret
        runtime.settings.TELEGRAM_WEBHOOK_DROP_PENDING_ON_SET = original_drop_on_set
        runtime.set_webhook = original_set_webhook
        runtime.delete_webhook = original_delete_webhook


def test_sync_webhook_mode_deletes_when_polling_enabled() -> None:
    original_autosync = runtime.settings.TELEGRAM_WEBHOOK_AUTOSYNC_ON_STARTUP
    original_use_webhook = runtime.settings.TELEGRAM_USE_WEBHOOK
    original_drop_on_disable = runtime.settings.TELEGRAM_WEBHOOK_DROP_PENDING_ON_DISABLE
    original_delete_webhook = runtime.delete_webhook

    calls: dict[str, object] = {}
    try:
        runtime.settings.TELEGRAM_WEBHOOK_AUTOSYNC_ON_STARTUP = True
        runtime.settings.TELEGRAM_USE_WEBHOOK = False
        runtime.settings.TELEGRAM_WEBHOOK_DROP_PENDING_ON_DISABLE = True

        async def _fake_delete_webhook(drop_pending_updates: bool = False) -> bool:
            calls["delete_drop"] = drop_pending_updates
            return True

        runtime.delete_webhook = _fake_delete_webhook
        result = asyncio.run(runtime.sync_webhook_mode())
        assert result["action"] == "deleted"
        assert calls["delete_drop"] is True
    finally:
        runtime.settings.TELEGRAM_WEBHOOK_AUTOSYNC_ON_STARTUP = original_autosync
        runtime.settings.TELEGRAM_USE_WEBHOOK = original_use_webhook
        runtime.settings.TELEGRAM_WEBHOOK_DROP_PENDING_ON_DISABLE = original_drop_on_disable
        runtime.delete_webhook = original_delete_webhook


def test_sync_webhook_mode_skips_when_url_missing() -> None:
    original_autosync = runtime.settings.TELEGRAM_WEBHOOK_AUTOSYNC_ON_STARTUP
    original_use_webhook = runtime.settings.TELEGRAM_USE_WEBHOOK
    original_url = runtime.settings.TELEGRAM_WEBHOOK_URL
    try:
        runtime.settings.TELEGRAM_WEBHOOK_AUTOSYNC_ON_STARTUP = True
        runtime.settings.TELEGRAM_USE_WEBHOOK = True
        runtime.settings.TELEGRAM_WEBHOOK_URL = ""
        result = asyncio.run(runtime.sync_webhook_mode())
        assert result["action"] == "skipped"
        assert result["reason"] == "missing_webhook_url"
    finally:
        runtime.settings.TELEGRAM_WEBHOOK_AUTOSYNC_ON_STARTUP = original_autosync
        runtime.settings.TELEGRAM_USE_WEBHOOK = original_use_webhook
        runtime.settings.TELEGRAM_WEBHOOK_URL = original_url
