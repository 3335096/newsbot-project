from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import html
from typing import Any

from aiogram import Bot
from sqlalchemy.orm import Session

from app.db.models.article_draft import ArticleDraft
from app.db.models.article_raw import ArticleRaw
from app.db.models.publication import Publication
TELEGRAM_MESSAGE_LIMIT = 4096
TELEGRAM_CAPTION_LIMIT = 1024


@dataclass
class PublishResult:
    publication: Publication
    sent_message_ids: list[int]


class PublisherService:
    def __init__(self, bot: Bot):
        self.bot = bot

    async def create_publication(
        self,
        db: Session,
        *,
        draft_id: int,
        channel_key: str,
        publish_now: bool = True,
        scheduled_at: datetime | None = None,
    ) -> Publication:
        channel_id = self._resolve_channel_id(channel_key)
        draft = db.query(ArticleDraft).filter(ArticleDraft.id == draft_id).first()
        if not draft:
            raise ValueError("Draft not found")

        existing = (
            db.query(Publication)
            .filter(Publication.draft_id == draft_id, Publication.channel_id == channel_id)
            .first()
        )
        if existing and existing.status in {"queued", "scheduled", "published"}:
            return existing

        status = "queued" if publish_now else "scheduled"
        publication = Publication(
            draft_id=draft_id,
            channel_id=channel_id,
            status=status,
            scheduled_at=scheduled_at if not publish_now else None,
            target_language=draft.target_language,
        )
        db.add(publication)
        db.commit()
        db.refresh(publication)
        return publication

    async def process_publication(
        self,
        db: Session,
        publication: Publication,
    ) -> PublishResult:
        draft = db.query(ArticleDraft).filter(ArticleDraft.id == publication.draft_id).first()
        if not draft:
            publication.status = "error"
            publication.log = "Draft not found for publication"
            db.commit()
            db.refresh(publication)
            return PublishResult(publication=publication, sent_message_ids=[])

        raw = None
        if draft.article_raw_id:
            raw = db.query(ArticleRaw).filter(ArticleRaw.id == draft.article_raw_id).first()

        rendered = self.render_post(
            title=draft.title_translated or (raw.title_raw if raw else None),
            content=draft.content_translated or (raw.content_raw if raw else None),
            source_url=raw.url if raw else None,
        )
        media_url = self._pick_media_url(draft.media)
        chunks = self.split_for_telegram(rendered)

        message_ids: list[int] = []
        try:
            if chunks:
                first_chunk = chunks[0]
                from core.config import settings
                if media_url and settings.ENABLE_IMAGES:
                    sent = await self.bot.send_photo(
                        chat_id=publication.channel_id,
                        photo=media_url,
                        caption=self._fit_caption(first_chunk),
                        parse_mode="HTML",
                    )
                    message_ids.append(sent.message_id)
                    for part in chunks[1:]:
                        msg = await self.bot.send_message(
                            chat_id=publication.channel_id,
                            text=part,
                            parse_mode="HTML",
                        )
                        message_ids.append(msg.message_id)
                else:
                    for part in chunks:
                        msg = await self.bot.send_message(
                            chat_id=publication.channel_id,
                            text=part,
                            parse_mode="HTML",
                        )
                        message_ids.append(msg.message_id)

            publication.message_id = message_ids[0] if message_ids else None
            publication.status = "published"
            publication.published_at = datetime.now(timezone.utc)
            publication.log = f"Published messages: {message_ids}"
            draft.status = "published"
            db.commit()
            db.refresh(publication)
            return PublishResult(publication=publication, sent_message_ids=message_ids)
        except Exception as exc:
            publication.status = "error"
            publication.log = str(exc)
            db.commit()
            db.refresh(publication)
            return PublishResult(publication=publication, sent_message_ids=[])

    async def process_due_publications(self, db: Session) -> int:
        now_utc = datetime.now(timezone.utc)
        queued = db.query(Publication).filter(Publication.status == "queued").all()
        scheduled = (
            db.query(Publication)
            .filter(Publication.status == "scheduled", Publication.scheduled_at <= now_utc)
            .all()
        )
        items = queued + scheduled
        processed = 0
        for publication in items:
            await self.process_publication(db, publication)
            processed += 1
        return processed

    @staticmethod
    def render_post(
        *,
        title: str | None,
        content: str | None,
        source_url: str | None,
    ) -> str:
        safe_title = html.escape((title or "").strip())
        safe_content = html.escape((content or "").strip())
        safe_source = html.escape((source_url or "").strip())

        parts: list[str] = []
        if safe_title:
            parts.append(f"<b>{safe_title}</b>")
        if safe_content:
            parts.append(safe_content)
        if safe_source:
            parts.append(f'<a href="{safe_source}">Источник</a>')
        return "\n\n".join([p for p in parts if p]).strip()

    @staticmethod
    def split_for_telegram(text: str, limit: int = TELEGRAM_MESSAGE_LIMIT) -> list[str]:
        text = (text or "").strip()
        if not text:
            return []
        if len(text) <= limit:
            return [text]

        chunks: list[str] = []
        start = 0
        while start < len(text):
            end = min(start + limit, len(text))
            if end < len(text):
                split_idx = text.rfind("\n", start, end)
                if split_idx <= start:
                    split_idx = text.rfind(" ", start, end)
                if split_idx > start:
                    end = split_idx
            chunk = text[start:end].strip()
            if chunk:
                chunks.append(chunk)
            start = end if end > start else start + limit
        return chunks

    @staticmethod
    def _fit_caption(text: str) -> str:
        if len(text) <= TELEGRAM_CAPTION_LIMIT:
            return text
        return text[: TELEGRAM_CAPTION_LIMIT - 1].rstrip() + "…"

    @staticmethod
    def _pick_media_url(media: Any) -> str | None:
        if not media:
            return None
        if isinstance(media, list):
            for item in media:
                if isinstance(item, dict):
                    maybe = item.get("url")
                    if maybe:
                        return str(maybe)
                elif isinstance(item, str):
                    return item
        return None

    @staticmethod
    def _resolve_channel_id(channel_key: str) -> int:
        from core.config import settings

        channel_id = settings.channel_ids.get(channel_key)
        if not channel_id:
            raise ValueError(f"Channel '{channel_key}' not found in TELEGRAM_CHANNEL_IDS")
        return channel_id
