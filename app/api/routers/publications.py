from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db.models.publication import Publication
from app.db.session import get_db
from app.services.publisher_service import PublisherService
from app.services.queue_dispatcher import enqueue_publication

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


class RetryPublicationPayload(BaseModel):
    force: bool = True


@router.post("", response_model=PublicationOut)
async def create_publication(payload: PublicationCreatePayload, db: Session = Depends(get_db)):
    try:
        publisher = PublisherService(bot=None)
        publication = await publisher.create_publication(
            db,
            draft_id=payload.draft_id,
            channel_key=payload.channel,
            publish_now=payload.publish_now,
            scheduled_at=payload.scheduled_at,
        )
        if payload.publish_now and publication.status == "queued":
            enqueue_publication(db, publication, force=False)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

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


@router.post("/{publication_id}/retry", response_model=PublicationOut)
async def retry_publication(
    publication_id: int,
    payload: RetryPublicationPayload,
    db: Session = Depends(get_db),
):
    publication = db.query(Publication).filter(Publication.id == publication_id).first()
    if not publication:
        raise HTTPException(status_code=404, detail="Publication not found")

    if publication.status not in {"error", "queued", "scheduled"}:
        raise HTTPException(status_code=409, detail="Publication cannot be retried in current state")

    if enqueue_publication(db, publication, force=payload.force) is None:
        raise HTTPException(status_code=409, detail="Publication was not enqueued")

    db.refresh(publication)
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
