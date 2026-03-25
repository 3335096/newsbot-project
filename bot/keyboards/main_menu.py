from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

main_menu_kb = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="Drafts", callback_data="show_drafts")],
    [InlineKeyboardButton(text="Sources", callback_data="show_sources")],
    [InlineKeyboardButton(text="Moderation Rules", callback_data="show_moderation_rules")],
    [InlineKeyboardButton(text="Settings", callback_data="show_settings")]
])
