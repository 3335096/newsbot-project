from aiogram import Bot
from core.config import settings

class PublisherService:
    def __init__(self, bot: Bot):
        self.bot = bot

    async def publish_draft(self, channel_name: str, title: str, content: str, media_url: str | None = None):
        channel_id = settings.channel_ids.get(channel_name)
        if not channel_id:
            raise ValueError(f"Channel {channel_name} not found in settings")

        message_text = f"**{title}**\n\n{content}"
        if media_url and settings.ENABLE_IMAGES:
            message = await self.bot.send_photo(chat_id=channel_id, photo=media_url, caption=message_text, parse_mode="Markdown")
        else:
            message = await self.bot.send_message(chat_id=channel_id, text=message_text, parse_mode="Markdown")
        
        return message.message_id
