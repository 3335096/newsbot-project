from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.services.moderation_service import ModerationService

router = APIRouter(prefix="/moderation", tags=["moderation"])


class ModerationRuleOut(BaseModel):
    id: int
    kind: str
    pattern: str
    action: str
    enabled: bool
    comment: str | None


class ModerationRuleCreatePayload(BaseModel):
    kind: str
    pattern: str
    action: str
    enabled: bool = True
    comment: str | None = None


@router.get("/rules", response_model=list[ModerationRuleOut])
async def list_rules(db: Session = Depends(get_db)):
    service = ModerationService(db)
    rules = service.list_rules()
    return [
        {
            "id": r.id,
            "kind": r.kind,
            "pattern": r.pattern,
            "action": r.action,
            "enabled": r.enabled,
            "comment": r.comment,
        }
        for r in rules
    ]


@router.post("/rules", response_model=ModerationRuleOut)
async def create_rule(payload: ModerationRuleCreatePayload, db: Session = Depends(get_db)):
    service = ModerationService(db)
    try:
        rule = service.create_rule(
            kind=payload.kind,
            pattern=payload.pattern,
            action=payload.action,
            enabled=payload.enabled,
            comment=payload.comment,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return {
        "id": rule.id,
        "kind": rule.kind,
        "pattern": rule.pattern,
        "action": rule.action,
        "enabled": rule.enabled,
        "comment": rule.comment,
    }


@router.post("/rules/{rule_id}/toggle", response_model=ModerationRuleOut)
async def toggle_rule(rule_id: int, db: Session = Depends(get_db)):
    service = ModerationService(db)
    try:
        rule = service.toggle_rule(rule_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    return {
        "id": rule.id,
        "kind": rule.kind,
        "pattern": rule.pattern,
        "action": rule.action,
        "enabled": rule.enabled,
        "comment": rule.comment,
    }
