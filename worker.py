from __future__ import annotations

import threading
import time

from rq import Connection, Worker

from app.queue import get_redis_connection
from app.services.worker_state import heartbeat_worker
from core.config import settings


def main() -> None:
    connection = get_redis_connection()
    queue_names = [settings.QUEUE_LLM_NAME, settings.QUEUE_PUBLICATIONS_NAME]
    stop_event = threading.Event()

    def _heartbeat_loop() -> None:
        while not stop_event.is_set():
            try:
                heartbeat_worker()
            except Exception:
                # Keep worker process alive even if heartbeat fails temporarily.
                pass
            stop_event.wait(10)

    heartbeat_thread = threading.Thread(target=_heartbeat_loop, daemon=True)
    heartbeat_thread.start()
    with Connection(connection):
        worker = Worker(queue_names)
        try:
            worker.work()
        finally:
            stop_event.set()
            heartbeat_thread.join(timeout=2)


if __name__ == "__main__":
    main()
