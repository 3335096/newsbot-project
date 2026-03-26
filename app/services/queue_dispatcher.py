from __future__ import annotations

from datetime import datetime, timezone

from rq import Queue
from sqlalchemy.orm import Session

from app.db.models.llm_task import LLMTask
from app.db.models.publication import Publication
from app.queue import (
    fetch_job,
    default_retry_policy,
    get_llm_queue,
    get_publications_queue,
)
from core.config import settings


def _to_aware_utc(dt: datetime | None) -> datetime | None:
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def enqueue_llm_task(
    db: Session,
    task: LLMTask,
    *,
    max_len: int = 700,
    queue: Queue | None = None,
) -> str:
    active_queue = queue or get_llm_queue()
    job = active_queue.enqueue(
        "app.services.background_jobs.run_llm_task_job",
        task.id,
        draft_id=task.draft_id,
        task_type=task.task_type,
        preset_name=task.preset,
        model=task.model,
        max_len=max_len,
        retry=default_retry_policy(),
        result_ttl=settings.QUEUE_RESULT_TTL_SECONDS,
        on_failure="app.services.background_jobs.enqueue_failed_marker",
    )
    task.queue_job_id = job.id
    task.status = "queued"
    task.error = None
    db.commit()
    return job.id


def enqueue_publication(
    db: Session,
    publication: Publication,
    *,
    queue: Queue | None = None,
    force: bool = False,
) -> str | None:
    if publication.status not in {"queued", "scheduled"}:
        return None
    if publication.status == "scheduled":
        scheduled_at = _to_aware_utc(publication.scheduled_at)
        if not scheduled_at:
            return None
        if scheduled_at > datetime.now(timezone.utc):
            return None
        publication.status = "queued"

    already_enqueued = bool(publication.queue_job_id)
    if already_enqueued and not force:
        return None

    active_queue = queue or get_publications_queue()
    job = active_queue.enqueue(
        "app.services.background_jobs.process_publication_job",
        publication.id,
        retry=default_retry_policy(),
        result_ttl=settings.QUEUE_RESULT_TTL_SECONDS,
        on_failure="app.services.background_jobs.enqueue_failed_marker",
    )
    publication.queue_job_id = job.id
    publication.log = f"enqueued_job:{job.id}"
    db.commit()
    return job.id


def enqueue_due_publications(db: Session, queue: Queue | None = None) -> int:
    now_utc = datetime.now(timezone.utc)
    queued = db.query(Publication).filter(Publication.status == "queued").all()
    scheduled = (
        db.query(Publication)
        .filter(Publication.status == "scheduled", Publication.scheduled_at <= now_utc)
        .all()
    )

    enqueued = 0
    for publication in queued + scheduled:
        if enqueue_publication(db, publication, queue=queue):
            enqueued += 1
    return enqueued


def requeue_job_by_id(job_id: str) -> bool:
    job = fetch_job(job_id)
    if not job:
        return False
    try:
        status = job.get_status(refresh=True)
        if status not in {"failed", "stopped", "canceled"}:
            return False
        origin = getattr(job, "origin", None)
        if origin:
            job.requeue(queue=get_queue(origin))
        else:
            job.requeue()
        return True
    except Exception:
        return False


def requeue_job_object(job) -> bool:
    try:
        if job.get_status(refresh=True) not in {"failed", "stopped", "canceled"}:
            return False
        job.requeue()
        return True
    except Exception:
        return False

