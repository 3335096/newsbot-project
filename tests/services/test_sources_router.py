from __future__ import annotations

import os
from unittest.mock import AsyncMock

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool
from sqlalchemy.orm import Session, sessionmaker

os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("TELEGRAM_BOT_TOKEN", "test-token")

from app.db.models.base import Base
from app.db.models.source import Source
from app.main import app
from app.api.routers import sources as sources_router
from app.db.session import get_db


def _db_session() -> Session:
    engine = create_engine(
        "sqlite://",
        future=True,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    testing_session = sessionmaker(bind=engine, autocommit=False, autoflush=False, future=True)
    return testing_session()


def test_create_source_rejects_invalid_cron() -> None:
    db = _db_session()

    def _override_get_db():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = _override_get_db
    client = TestClient(app)
    response = client.post(
        "/api/sources",
        json={
            "name": "Feed 1",
            "type": "rss",
            "url": "https://example.com/feed.xml",
            "schedule_cron": "invalid cron",
        },
    )
    assert response.status_code == 400
    assert "Invalid cron expression" in response.json()["detail"]

    app.dependency_overrides.clear()


def test_create_source_and_parse_now_returns_stats() -> None:
    db = _db_session()
    sync_calls: list[tuple[int, str | None, bool]] = []

    def _override_get_db():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = _override_get_db
    client = TestClient(app)

    create_response = client.post(
        "/api/sources",
        json={
            "name": "Feed 2",
            "type": "rss",
            "url": "https://example.com/feed2.xml",
            "enabled": True,
            "schedule_cron": "*/5 * * * *",
            "translate_enabled": True,
            "default_target_language": "ru",
        },
    )
    assert create_response.status_code == 200
    source = create_response.json()
    assert source["name"] == "Feed 2"
    assert source["schedule_cron"] == "*/5 * * * *"

    original_process_source = sources_router.ParserService.process_source
    original_sync_source_job = sources_router.scheduler.sync_source_job
    try:
        sources_router.scheduler.sync_source_job = lambda source_id, cron_schedule, enabled: sync_calls.append(
            (source_id, cron_schedule, enabled)
        )
        sources_router.ParserService.process_source = AsyncMock(
            return_value={"processed": 3, "created": 2, "drafts_created": 1}
        )
        parse_response = client.post(f"/api/sources/{source['id']}/parse-now")
        assert parse_response.status_code == 200
        payload = parse_response.json()
        assert payload["source_id"] == source["id"]
        assert payload["processed"] == 3
        assert payload["created"] == 2
        assert payload["drafts_created"] == 1
    finally:
        sources_router.ParserService.process_source = original_process_source
        sources_router.scheduler.sync_source_job = original_sync_source_job
        app.dependency_overrides.clear()


def test_update_source_toggles_enabled() -> None:
    db = _db_session()
    sync_calls: list[tuple[int, str | None, bool]] = []
    source = Source(name="Feed 3", type="rss", url="https://example.com/feed3.xml", enabled=True)
    db.add(source)
    db.commit()
    db.refresh(source)

    def _override_get_db():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = _override_get_db
    client = TestClient(app)

    original_sync_source_job = sources_router.scheduler.sync_source_job
    try:
        sources_router.scheduler.sync_source_job = lambda source_id, cron_schedule, enabled: sync_calls.append(
            (source_id, cron_schedule, enabled)
        )
        response = client.put(f"/api/sources/{source.id}", json={"enabled": False})
        assert response.status_code == 200
        payload = response.json()
        assert payload["enabled"] is False
        assert len(sync_calls) == 1
        assert sync_calls[0] == (source.id, source.schedule_cron, False)
    finally:
        sources_router.scheduler.sync_source_job = original_sync_source_job
        app.dependency_overrides.clear()


def test_parse_now_returns_409_for_disabled_source() -> None:
    db = _db_session()
    source = Source(
        name="Feed 4",
        type="rss",
        url="https://example.com/feed4.xml",
        enabled=False,
    )
    db.add(source)
    db.commit()
    db.refresh(source)

    def _override_get_db():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = _override_get_db
    client = TestClient(app)
    response = client.post(f"/api/sources/{source.id}/parse-now")
    assert response.status_code == 409
    assert "disabled" in response.json()["detail"]
    app.dependency_overrides.clear()
