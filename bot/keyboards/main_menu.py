from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo

from core.config import settings


def build_main_menu_kb() -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(text="Черновики", callback_data="show_drafts")],
        [InlineKeyboardButton(text="Источники", callback_data="show_sources")],
        [InlineKeyboardButton(text="Операции", callback_data="show_ops")],
        [InlineKeyboardButton(text="Настройки", callback_data="show_settings")],
    ]

    web_app_url = settings.WEB_APP_URL.strip()
    if web_app_url:
        rows.append(
            [
                InlineKeyboardButton(
                    text="Веб-панель",
                    web_app=WebAppInfo(url=web_app_url),
                )
            ]
        )
    return InlineKeyboardMarkup(inline_keyboard=rows)
