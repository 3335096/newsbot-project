from __future__ import annotations

import os

os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("TELEGRAM_BOT_TOKEN", "test-token")

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.models.base import Base
from app.main import app
from app.api.routers import users as users_router


def _testing_sessionmaker() -> sessionmaker:
    engine = create_engine(
        "sqlite://",
        future=True,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    return sessionmaker(bind=engine, autocommit=False, autoflush=False, future=True)


def test_user_can_get_own_settings_with_actor_user_id() -> None:
    testing_session = _testing_sessionmaker()
    client = TestClient(app)
    original_session_local = users_router.SessionLocal
    try:
        users_router.SessionLocal = testing_session
        response = client.get("/api/users/1002/settings?actor_user_id=1002")
        assert response.status_code == 200
        payload = response.json()
        assert payload["telegram_user_id"] == 1002
        assert payload["settings"]["default_target_language"]
        assert isinstance(payload["settings"]["enable_images"], bool)
    finally:
        users_router.SessionLocal = original_session_local


def test_user_cannot_get_other_user_settings_without_admin_role() -> None:
    testing_session = _testing_sessionmaker()
    client = TestClient(app)
    original_session_local = users_router.SessionLocal
    try:
        users_router.SessionLocal = testing_session
        response = client.get("/api/users/2002/settings?actor_user_id=2001")
        assert response.status_code == 403
        assert response.json()["detail"] == "Not enough permissions"
    finally:
        users_router.SessionLocal = original_session_local


def test_user_can_update_own_settings_with_actor_user_id() -> None:
    testing_session = _testing_sessionmaker()
    client = TestClient(app)
    original_session_local = users_router.SessionLocal
    try:
        users_router.SessionLocal = testing_session
        response = client.post(
            "/api/users/1002/settings?actor_user_id=1002",
            json={"default_target_language": "en", "enable_images": False},
        )
        assert response.status_code == 200
        payload = response.json()
        assert payload["telegram_user_id"] == 1002
        assert payload["settings"]["default_target_language"] == "en"
        assert payload["settings"]["enable_images"] is False
    finally:
        users_router.SessionLocal = original_session_local
