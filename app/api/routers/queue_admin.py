from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.metrics import observe_queue_depth, record_queue_event
from app.queue import (
    fetch_job,
    get_failed_queue,
    get_redis_connection,
    queue_snapshot,
)
from app.services.queue_dispatcher import requeue_job_object
from app.services.worker_state import get_worker_last_seen, is_worker_alive
from core.config import settings

router = APIRouter(prefix="/queue", tags=["queue"])


class QueueStatsOut(BaseModel):
    name: str
    queued: int
    started: int
    finished: int
    failed: int
    deferred: int
    scheduled: int


class QueueOverviewOut(BaseModel):
    queues: list[QueueStatsOut]
    redis_ok: bool
    worker_alive: bool
    worker_last_seen_ts: int | None
    worker_last_seen_iso: str | None


class RequeueOut(BaseModel):
    job_id: str
    status: str


def _to_stats_out(snapshot) -> QueueStatsOut:
    observe_queue_depth(snapshot.name, snapshot.queued)
    return QueueStatsOut(
        name=snapshot.name,
        queued=snapshot.queued,
        started=snapshot.started,
        finished=snapshot.finished,
        failed=snapshot.failed,
        deferred=snapshot.deferred,
        scheduled=snapshot.scheduled,
    )


@router.get("/stats", response_model=QueueOverviewOut)
async def get_queue_stats():
    queue_names = [
        settings.QUEUE_LLM_NAME,
        settings.QUEUE_PUBLICATIONS_NAME,
        settings.QUEUE_FAILED_NAME,
    ]
    snapshots = [_to_stats_out(queue_snapshot(name)) for name in queue_names]

    last_seen = get_worker_last_seen()
    last_seen_iso = None
    if last_seen is not None:
        last_seen_iso = datetime.fromtimestamp(last_seen, tz=timezone.utc).isoformat()

    redis_ok = True
    try:
        get_redis_connection().ping()
    except Exception:
        redis_ok = False

    return QueueOverviewOut(
        queues=snapshots,
        redis_ok=redis_ok,
        worker_alive=is_worker_alive(),
        worker_last_seen_ts=last_seen,
        worker_last_seen_iso=last_seen_iso,
    )


@router.post("/failed/{job_id}/requeue", response_model=RequeueOut)
async def requeue_failed_job(job_id: str):
    marker = fetch_job(f"failed_{job_id}")
    if marker is None:
        raise HTTPException(status_code=404, detail="Failed marker job not found")

    original = fetch_job(job_id)
    if original is None:
        raise HTTPException(status_code=404, detail="Original job not found")

    if not requeue_job_object(original):
        raise HTTPException(status_code=409, detail="Failed to requeue job")

    failed_queue = get_failed_queue()
    try:
        failed_queue.remove(marker)
    except Exception:
        pass

    record_queue_event(event="manual_requeue", queue_name=settings.QUEUE_FAILED_NAME)
    return RequeueOut(job_id=job_id, status="requeued")
