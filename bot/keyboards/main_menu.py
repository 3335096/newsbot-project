from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

main_menu_kb = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="Черновики", callback_data="show_drafts")],
    [InlineKeyboardButton(text="Источники", callback_data="show_sources")],
    [InlineKeyboardButton(text="Операции", callback_data="show_ops")],
    [InlineKeyboardButton(text="Правила модерации", callback_data="show_moderation_rules")],
    [InlineKeyboardButton(text="Настройки", callback_data="show_settings")]
])
