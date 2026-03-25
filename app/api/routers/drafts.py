from typing import List, Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.db.models.article_draft import ArticleDraft

router = APIRouter()

class DraftRejectPayload(BaseModel):
    reason: str


class DraftOut(BaseModel):
    id: int
    title_translated: str | None
    status: Literal["new", "flagged", "approved", "rejected", "published"]


@router.get("/drafts", response_model=List[DraftOut])
async def get_drafts(db: Session = Depends(get_db)):
    drafts = db.query(ArticleDraft).all()
    return [{"id": draft.id, "title_translated": draft.title_translated, "status": draft.status} for draft in drafts]

@router.post("/drafts/{draft_id}/approve")
async def approve_draft(draft_id: int, db: Session = Depends(get_db)):
    draft = db.query(ArticleDraft).filter(ArticleDraft.id == draft_id).first()
    if not draft:
        raise HTTPException(status_code=404, detail="Draft not found")
    draft.status = "approved"
    db.commit()
    return {"message": f"Draft {draft_id} approved"}

@router.post("/drafts/{draft_id}/reject")
async def reject_draft(draft_id: int, payload: DraftRejectPayload, db: Session = Depends(get_db)):
    draft = db.query(ArticleDraft).filter(ArticleDraft.id == draft_id).first()
    if not draft:
        raise HTTPException(status_code=404, detail="Draft not found")
    draft.status = "rejected"
    draft.rejection_reason = payload.reason
    db.commit()
    return {"message": f"Draft {draft_id} rejected with reason: {payload.reason}"}
