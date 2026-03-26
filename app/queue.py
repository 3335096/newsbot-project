from __future__ import annotations

from redis import Redis
from rq import Queue, Retry

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


def default_retry_policy() -> Retry:
    # Exponential style intervals for transient network/API issues.
    return Retry(max=settings.QUEUE_JOB_RETRIES, interval=[5, 15, 30])

