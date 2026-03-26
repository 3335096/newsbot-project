from __future__ import annotations

from rq import Connection, Worker

from app.queue import get_redis_connection
from core.config import settings


def main() -> None:
    connection = get_redis_connection()
    queue_names = [settings.QUEUE_LLM_NAME, settings.QUEUE_PUBLICATIONS_NAME]
    with Connection(connection):
        worker = Worker(queue_names)
        worker.work()


if __name__ == "__main__":
    main()
