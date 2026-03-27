from __future__ import annotations

import os

os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("TELEGRAM_BOT_TOKEN", "test-token")
os.environ.setdefault("TELEGRAM_ADMIN_IDS", "1001")
os.environ.setdefault("TELEGRAM_ALLOWED_USER_IDS", "1001,1002")

from bot.handlers import settings


def test_settings_keyboard_has_expected_actions() -> None:
    payload = {"settings": {"enable_images": True, "default_target_language": "ru"}}
    kb = settings._settings_keyboard(payload)
    callback_data = [btn.callback_data for row in kb.inline_keyboard for btn in row]
    assert "settings_edit_default_lang" in callback_data
    assert "settings_toggle_images" in callback_data


def test_settings_text_renders_core_values() -> None:
    payload = {
        "settings": {
            "default_target_language": "ru",
            "enable_images": True,
        }
    }
    text = settings._settings_text(payload)
    assert "default_target_language: ru" in text
    assert "enable_images: True" in text


def test_settings_request_params_include_actor_user_id() -> None:
    params = settings._settings_request_params(12345)
    assert params == {"actor_user_id": 12345}
