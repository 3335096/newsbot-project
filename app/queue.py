from __future__ import annotations

from dataclasses import dataclass

from redis import Redis
from rq import Queue, Retry
from rq.job import Job

from core.config import settings


def get_redis_connection() -> Redis:
    return Redis.from_url(settings.REDIS_URL)


def get_queue(name: str) -> Queue:
    return Queue(
        name=name,
        connection=get_redis_connection(),
        default_timeout=settings.QUEUE_DEFAULT_TIMEOUT_SECONDS,
    )


def get_llm_queue() -> Queue:
    return get_queue(settings.QUEUE_LLM_NAME)


def get_publications_queue() -> Queue:
    return get_queue(settings.QUEUE_PUBLICATIONS_NAME)


def get_failed_queue() -> Queue:
    return get_queue(settings.QUEUE_FAILED_NAME)


def default_retry_policy() -> Retry:
    # Exponential style intervals for transient network/API issues.
    return Retry(max=settings.QUEUE_JOB_RETRIES, interval=[5, 15, 30])


@dataclass
class QueueSnapshot:
    name: str
    queued: int
    started: int
    finished: int
    failed: int
    deferred: int
    scheduled: int


def queue_snapshot(queue_name: str) -> QueueSnapshot:
    queue = get_queue(queue_name)
    return QueueSnapshot(
        name=queue_name,
        queued=queue.count,
        started=queue.started_job_registry.count,
        finished=queue.finished_job_registry.count,
        failed=queue.failed_job_registry.count,
        deferred=queue.deferred_job_registry.count,
        scheduled=queue.scheduled_job_registry.count,
    )


def fetch_job(job_id: str) -> Job | None:
    try:
        return Job.fetch(job_id, connection=get_redis_connection())
    except Exception:
        return None

