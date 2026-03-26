from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db.models.user import User
from app.db.session import SessionLocal
from core.config import settings

router = APIRouter(prefix="/users", tags=["users"])


class UserSettingsOut(BaseModel):
    telegram_user_id: int
    role: str
    settings: dict


class UserSettingsUpdatePayload(BaseModel):
    default_target_language: str | None = None
    enable_images: bool | None = None


def _get_or_create_user(db: Session, telegram_user_id: int) -> User:
    user = db.query(User).filter(User.telegram_user_id == telegram_user_id).first()
    if user:
        return user
    role = "admin" if telegram_user_id in settings.admin_ids else "editor"
    user = User(
        telegram_user_id=telegram_user_id,
        role=role,
        display_name=None,
        settings={},
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def _ensure_caller_can_manage(
    *,
    target_user_id: int,
    actor_user_id: int | None,
    actor_role: str | None,
) -> None:
    if actor_user_id is None:
        raise HTTPException(status_code=400, detail="actor_user_id is required")
    if actor_user_id == target_user_id:
        return
    if actor_role == "admin":
        return
    raise HTTPException(status_code=403, detail="Not enough permissions")


def _normalize_settings(payload: dict | None) -> dict:
    data = dict(payload or {})
    default_lang = str(data.get("default_target_language") or settings.DEFAULT_TARGET_LANGUAGE).strip().lower()
    if len(default_lang) < 2:
        default_lang = settings.DEFAULT_TARGET_LANGUAGE
    data["default_target_language"] = default_lang
    enable_images = data.get("enable_images")
    data["enable_images"] = bool(settings.ENABLE_IMAGES if enable_images is None else enable_images)
    return data


@router.get("/{telegram_user_id}/settings", response_model=UserSettingsOut)
async def get_user_settings(
    telegram_user_id: int,
    actor_user_id: int | None = None,
):
    db = SessionLocal()
    try:
        actor = None
        if actor_user_id is not None:
            actor = _get_or_create_user(db, actor_user_id)
        _ensure_caller_can_manage(
            target_user_id=telegram_user_id,
            actor_user_id=actor_user_id,
            actor_role=(actor.role if actor else None),
        )
        user = _get_or_create_user(db, telegram_user_id)
        normalized = _normalize_settings(user.settings)
        if normalized != (user.settings or {}):
            user.settings = normalized
            db.commit()
            db.refresh(user)
        return {
            "telegram_user_id": user.telegram_user_id,
            "role": user.role,
            "settings": normalized,
        }
    finally:
        db.close()


@router.post("/{telegram_user_id}/settings", response_model=UserSettingsOut)
async def update_user_settings(
    telegram_user_id: int,
    payload: UserSettingsUpdatePayload,
    actor_user_id: int | None = None,
):
    db = SessionLocal()
    try:
        actor = None
        if actor_user_id is not None:
            actor = _get_or_create_user(db, actor_user_id)
        _ensure_caller_can_manage(
            target_user_id=telegram_user_id,
            actor_user_id=actor_user_id,
            actor_role=(actor.role if actor else None),
        )
        user = _get_or_create_user(db, telegram_user_id)
        current = _normalize_settings(user.settings)

        if payload.default_target_language is not None:
            lang = payload.default_target_language.strip().lower()
            if len(lang) < 2:
                raise HTTPException(status_code=400, detail="default_target_language is too short")
            current["default_target_language"] = lang
        if payload.enable_images is not None:
            current["enable_images"] = payload.enable_images

        user.settings = current
        db.commit()
        db.refresh(user)
        return {
            "telegram_user_id": user.telegram_user_id,
            "role": user.role,
            "settings": current,
        }
    finally:
        db.close()
