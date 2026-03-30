from __future__ import annotations

import os

os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("TELEGRAM_BOT_TOKEN", "test-token")

from bot.handlers import drafts


def test_card_keyboard_with_no_channels_keeps_actions() -> None:
    original_channel_ids = drafts.settings.channel_ids
    try:
        drafts.settings.TELEGRAM_CHANNEL_IDS = "{}"
        keyboard = drafts._card_keyboard(draft_id=1, view_mode="translated")
        buttons = [btn.text for row in keyboard.inline_keyboard for btn in row]
        assert "Кратко (Summary)" in buttons
        assert "Рерайт стиля" in buttons
        assert "Заголовок/Хэштеги" in buttons
        assert "Одобрить" in buttons
        assert "Отклонить" in buttons
        assert "Опубликовать: default" not in buttons
    finally:
        drafts.settings.TELEGRAM_CHANNEL_IDS = original_channel_ids


def test_card_keyboard_with_channels_shows_publish_buttons() -> None:
    original_channel_ids = drafts.settings.channel_ids
    try:
        drafts.settings.TELEGRAM_CHANNEL_IDS = '{"main": -1001111111111, "backup": -1002222222222}'
        keyboard = drafts._card_keyboard(draft_id=42, view_mode="translated")
        buttons = [btn.text for row in keyboard.inline_keyboard for btn in row]
        assert "Опубликовать: main" in buttons
        assert "Опубликовать: backup" in buttons
    finally:
        drafts.settings.TELEGRAM_CHANNEL_IDS = original_channel_ids


def test_compose_card_message_truncates_long_content() -> None:
    payload = {
        "id": 1,
        "status": "new",
        "source_language": "en",
        "target_language": "ru",
        "title_original": "Original",
        "content_original": "x" * 12000,
        "title_translated": "Translated",
        "content_translated": "y" * 12000,
        "flags": [],
    }
    text = drafts._card_text(payload, view_mode="translated")
    assert len(text) <= drafts.TELEGRAM_MESSAGE_LIMIT
    assert text.endswith("…")
