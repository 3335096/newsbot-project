from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db.models.publication import Publication
from app.db.session import get_db
from app.queue import get_failed_queue
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
    channel_alias: str | None
    message_id: int | None
    status: str
    scheduled_at: datetime | None
    published_at: datetime | None
    target_language: str
    log: str | None


class RetryPublicationPayload(BaseModel):
    force: bool = True


def _publication_to_out(publication: Publication) -> dict:
    return {
        "id": publication.id,
        "draft_id": publication.draft_id,
        "channel_id": publication.channel_id,
        "channel_alias": publication.channel_alias,
        "message_id": publication.message_id,
        "status": publication.status,
        "scheduled_at": publication.scheduled_at,
        "published_at": publication.published_at,
        "target_language": publication.target_language,
        "log": publication.log,
    }


@router.get("", response_model=list[PublicationOut])
async def list_publications(
    limit: int = 50,
    status: str | None = None,
    db: Session = Depends(get_db),
):
    safe_limit = max(1, min(limit, 200))
    query = db.query(Publication).order_by(Publication.id.desc())
    if status:
        query = query.filter(Publication.status == status)
    publications = query.limit(safe_limit).all()
    return [_publication_to_out(publication) for publication in publications]


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

    return _publication_to_out(publication)


@router.post("/{publication_id}/requeue-failed", response_model=PublicationOut)
async def requeue_failed_publication(
    publication_id: int,
    payload: RetryPublicationPayload,
    db: Session = Depends(get_db),
):
    publication = db.query(Publication).filter(Publication.id == publication_id).first()
    if not publication:
        raise HTTPException(status_code=404, detail="Publication not found")
    if publication.status != "error":
        raise HTTPException(status_code=409, detail="Only error publications can be requeued from failed queue")

    failed_queue = get_failed_queue()
    markers = [job for job in failed_queue.jobs if f"publication_{publication_id}" in (job.description or "")]
    if not markers and not payload.force:
        raise HTTPException(status_code=404, detail="No failed marker found for publication")

    publication.status = "queued"
    publication.queue_job_id = None
    publication.log = "Requeued from failed queue"
    db.commit()
    db.refresh(publication)

    enqueue_publication(db, publication, force=True)
    db.refresh(publication)
    return _publication_to_out(publication)


@router.get("/{publication_id}", response_model=PublicationOut)
async def get_publication(publication_id: int, db: Session = Depends(get_db)):
    publication = db.query(Publication).filter(Publication.id == publication_id).first()
    if not publication:
        raise HTTPException(status_code=404, detail="Publication not found")

    return _publication_to_out(publication)


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
    return _publication_to_out(publication)
