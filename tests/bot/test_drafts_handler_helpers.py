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
