from __future__ import annotations

import os

os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("TELEGRAM_BOT_TOKEN", "test-token")

from app.services.queue_dispatcher import requeue_job_object


class _FakeJob:
    def __init__(self, status: str):
        self._status = status
        self.requeued = False

    def get_status(self, refresh: bool = True) -> str:
        return self._status

    def requeue(self) -> None:
        self.requeued = True


def test_requeue_job_object_only_for_failed_like_status() -> None:
    failed_job = _FakeJob("failed")
    assert requeue_job_object(failed_job) is True
    assert failed_job.requeued is True

    started_job = _FakeJob("started")
    assert requeue_job_object(started_job) is False
    assert started_job.requeued is False
