from __future__ import annotations

import os

os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("TELEGRAM_BOT_TOKEN", "test-token")
os.environ.setdefault("TELEGRAM_ADMIN_IDS", "1001")
os.environ.setdefault("TELEGRAM_ALLOWED_USER_IDS", "1001,1002")

from bot.handlers import admin


def test_admin_keyboard_contains_expected_sections() -> None:
    kb = admin._admin_keyboard()
    callback_data = [btn.callback_data for row in kb.inline_keyboard for btn in row]
    assert "admin_llm_presets" in callback_data
    assert "admin_moderation_rules" in callback_data


def test_preset_action_keyboard_uses_preset_name_in_callbacks() -> None:
    kb = admin._preset_action_keyboard("summary")
    callback_data = [btn.callback_data for row in kb.inline_keyboard for btn in row]
    assert "admin_preset_edit_system_summary" in callback_data
    assert "admin_preset_edit_user_summary" in callback_data
    assert "admin_preset_edit_model_summary" in callback_data
    assert "admin_preset_toggle_summary" in callback_data


def test_admin_api_headers_uses_admin_api_token() -> None:
    original_admin = admin.settings.ADMIN_API_TOKEN
    admin.settings.ADMIN_API_TOKEN = "admin-token"
    try:
        headers = admin._admin_api_headers()
        assert headers == {"X-Admin-Api-Token": "admin-token"}
    finally:
        admin.settings.ADMIN_API_TOKEN = original_admin
