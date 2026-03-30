from __future__ import annotations

import os

os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("TELEGRAM_BOT_TOKEN", "test-token")

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.models.base import Base
from app.db.models.publication import Publication
from app.db.session import get_db
from app.main import app


def _build_test_client() -> tuple[TestClient, Session]:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    Base.metadata.create_all(bind=engine)

    def _override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = _override_get_db
    client = TestClient(app)
    db = TestingSessionLocal()
    return client, db


def test_list_publications_returns_latest_first_and_includes_channel_alias() -> None:
    client, db = _build_test_client()
    try:
        p1 = Publication(
            draft_id=1,
            channel_id=-1001,
            channel_alias="main",
            status="queued",
            target_language="ru",
            log=None,
        )
        p2 = Publication(
            draft_id=2,
            channel_id=-1002,
            channel_alias="backup",
            status="error",
            target_language="ru",
            log="failed",
        )
        db.add_all([p1, p2])
        db.commit()

        response = client.get("/api/publications?limit=10")
        assert response.status_code == 200
        payload = response.json()
        assert len(payload) == 2
        assert payload[0]["id"] == p2.id
        assert payload[0]["channel_alias"] == "backup"
        assert payload[1]["id"] == p1.id
        assert payload[1]["channel_alias"] == "main"
    finally:
        db.close()
        app.dependency_overrides.clear()


def test_list_publications_supports_status_filter() -> None:
    client, db = _build_test_client()
    try:
        db.add_all(
            [
                Publication(draft_id=10, channel_id=-1001, channel_alias="main", status="queued", target_language="ru"),
                Publication(draft_id=11, channel_id=-1001, channel_alias="main", status="error", target_language="ru"),
            ]
        )
        db.commit()

        response = client.get("/api/publications?status=error")
        assert response.status_code == 200
        payload = response.json()
        assert len(payload) == 1
        assert payload[0]["status"] == "error"
    finally:
        db.close()
        app.dependency_overrides.clear()
