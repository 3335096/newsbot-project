from fastapi import APIRouter

from app.queue import get_redis_connection, queue_snapshot
from app.services.worker_state import get_worker_last_seen, is_worker_alive
from core.config import settings

router = APIRouter()

@router.get("/health")
async def health_check():
    worker_alive = is_worker_alive()
    return {"status": "ok" if worker_alive else "degraded", "worker_alive": worker_alive}


@router.get("/health/ready")
async def readiness_check():
    redis_ok = False
    queue_stats = []
    try:
        redis = get_redis_connection()
        redis.ping()
        redis_ok = True
        for queue_name in (
            settings.QUEUE_LLM_NAME,
            settings.QUEUE_PUBLICATIONS_NAME,
            settings.QUEUE_FAILED_NAME,
        ):
            snap = queue_snapshot(queue_name)
            queue_stats.append(
                {
                    "name": snap.name,
                    "queued": snap.queued,
                    "started": snap.started,
                    "finished": snap.finished,
                    "failed": snap.failed,
                    "deferred": snap.deferred,
                    "scheduled": snap.scheduled,
                }
            )
    except Exception:
        redis_ok = False

    worker_alive = is_worker_alive()
    return {
        "status": "ok" if redis_ok else "degraded",
        "redis": {"ok": redis_ok},
        "worker": {
            "alive": worker_alive,
            "last_seen": get_worker_last_seen(),
        },
        "queues": queue_stats,
    }
