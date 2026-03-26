from __future__ import annotations

import os

os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("TELEGRAM_BOT_TOKEN", "test-token")
os.environ.setdefault("TELEGRAM_ADMIN_IDS", "1001")
os.environ.setdefault("TELEGRAM_ALLOWED_USER_IDS", "1001,1002")

from bot.handlers import sources


def test_source_text_uses_defaults_for_optional_fields() -> None:
    payload = {
        "id": 7,
        "name": "Tech Feed",
        "type": "rss",
        "url": "https://example.com/rss",
        "enabled": True,
        "schedule_cron": None,
        "translate_enabled": True,
        "default_target_language": None,
    }
    text = sources._source_text(payload)
    assert "Источник #7" in text
    assert "Cron: —" in text
    assert "Язык по умолчанию: ru" in text


def test_source_keyboard_contains_expected_actions() -> None:
    payload = {
        "id": 42,
        "name": "Site A",
        "type": "site",
        "url": "https://example.com",
        "enabled": False,
        "schedule_cron": "*/15 * * * *",
        "translate_enabled": True,
        "default_target_language": "ru",
    }
    kb = sources._source_keyboard(payload)
    callback_data = [btn.callback_data for row in kb.inline_keyboard for btn in row]
    assert "source_edit_name_42" in callback_data
    assert "source_edit_cron_42" in callback_data
    assert "source_edit_type_42" in callback_data
    assert "source_edit_url_42" in callback_data
    assert "source_edit_translate_42" in callback_data
    assert "source_edit_lang_42" in callback_data
    assert "source_parse_now_42" in callback_data
    assert "source_toggle:42:0" in callback_data
    assert "source_delete_42" in callback_data


def test_sources_actions_keyboard_has_create_button() -> None:
    kb = sources._sources_actions_keyboard()
    callback_data = [btn.callback_data for row in kb.inline_keyboard for btn in row]
    assert callback_data == ["source_create_start"]
