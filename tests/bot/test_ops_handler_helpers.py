from __future__ import annotations

import os

os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("TELEGRAM_BOT_TOKEN", "test-token")
os.environ.setdefault("TELEGRAM_ADMIN_IDS", "1001")
os.environ.setdefault("TELEGRAM_ALLOWED_USER_IDS", "1001,1002")

from bot.handlers import ops


def test_ops_keyboard_contains_actions() -> None:
    kb = ops._ops_keyboard()
    callback_data = [btn.callback_data for row in kb.inline_keyboard for btn in row]
    assert "ops_queue_stats" in callback_data
    assert "ops_readiness" in callback_data
    assert "ops_failed_list" in callback_data


def test_format_queue_stats_contains_core_fields() -> None:
    payload = {
        "redis_ok": True,
        "worker_alive": True,
        "worker_last_seen_iso": "2026-03-25T10:00:00+00:00",
        "queues": [
            {"name": "llm", "queued": 2, "started": 1, "failed": 0, "scheduled": 0},
            {"name": "publications", "queued": 0, "started": 0, "failed": 1, "scheduled": 3},
        ],
    }
    text = ops._format_queue_stats(payload)
    assert "Redis: OK" in text
    assert "Worker: alive" in text
    assert "- llm: queued=2" in text
    assert "- publications: queued=0" in text


def test_format_ready_contains_readiness_details() -> None:
    payload = {
        "status": "ok",
        "redis": {"ok": True},
        "worker": {"alive": True, "last_seen": 1711360800},
    }
    text = ops._format_ready(payload)
    assert "status=ok" in text
    assert "redis_ok=True" in text
    assert "worker_alive=True" in text


def test_failed_jobs_keyboard_contains_requeue_buttons() -> None:
    kb = ops._failed_jobs_keyboard(["job-1", "job-2"])
    callback_data = [btn.callback_data for row in kb.inline_keyboard for btn in row]
    assert "ops_requeue_failed:job-1" in callback_data
    assert "ops_requeue_failed:job-2" in callback_data
    assert "show_ops" in callback_data
