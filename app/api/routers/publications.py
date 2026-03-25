from __future__ import annotations

from datetime import datetime

from aiogram import Bot
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db.models.publication import Publication
from app.db.session import get_db
from app.services.publisher_service import PublisherService
from core.config import settings

router = APIRouter(prefix="/publications", tags=["publications"])


class PublicationCreatePayload(BaseModel):
    draft_id: int
    channel: str
    publish_now: bool = True
    scheduled_at: datetime | None = None


class PublicationOut(BaseModel):
    id: int
    draft_id: int | None
    channel_id: int | None
    message_id: int | None
    status: str
    scheduled_at: datetime | None
    published_at: datetime | None
    target_language: str
    log: str | None


@router.post("", response_model=PublicationOut)
async def create_publication(payload: PublicationCreatePayload, db: Session = Depends(get_db)):
    bot: Bot | None = None
    try:
        if payload.publish_now:
            bot = Bot(token=settings.TELEGRAM_BOT_TOKEN)
        publisher = PublisherService(bot)
        publication = await publisher.create_publication(
            db,
            draft_id=payload.draft_id,
            channel_key=payload.channel,
            publish_now=payload.publish_now,
            scheduled_at=payload.scheduled_at,
        )
        if payload.publish_now and publication.status == "queued":
            result = await publisher.process_publication(db, publication)
            publication = result.publication
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    finally:
        if bot is not None:
            await bot.session.close()

    return {
        "id": publication.id,
        "draft_id": publication.draft_id,
        "channel_id": publication.channel_id,
        "message_id": publication.message_id,
        "status": publication.status,
        "scheduled_at": publication.scheduled_at,
        "published_at": publication.published_at,
        "target_language": publication.target_language,
        "log": publication.log,
    }


@router.get("/{publication_id}", response_model=PublicationOut)
async def get_publication(publication_id: int, db: Session = Depends(get_db)):
    publication = db.query(Publication).filter(Publication.id == publication_id).first()
    if not publication:
        raise HTTPException(status_code=404, detail="Publication not found")

    return {
        "id": publication.id,
        "draft_id": publication.draft_id,
        "channel_id": publication.channel_id,
        "message_id": publication.message_id,
        "status": publication.status,
        "scheduled_at": publication.scheduled_at,
        "published_at": publication.published_at,
        "target_language": publication.target_language,
        "log": publication.log,
    }
