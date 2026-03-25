from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from app.db.session import get_db
from app.db.models.article_draft import ArticlesDraft

router = APIRouter()

@router.get("/drafts", response_model=List[dict])
async def get_drafts(db: Session = Depends(get_db)):
    drafts = db.query(ArticlesDraft).all()
    return [{"id": draft.id, "title_translated": draft.title_translated, "status": draft.status} for draft in drafts]

@router.post("/drafts/{draft_id}/approve")
async def approve_draft(draft_id: int, db: Session = Depends(get_db)):
    draft = db.query(ArticlesDraft).filter(ArticlesDraft.id == draft_id).first()
    if not draft:
        raise HTTPException(status_code=404, detail="Draft not found")
    draft.status = "approved"
    db.commit()
    return {"message": f"Draft {draft_id} approved"}

@router.post("/drafts/{draft_id}/reject")
async def reject_draft(draft_id: int, reason: str, db: Session = Depends(get_db)):
    draft = db.query(ArticlesDraft).filter(ArticlesDraft.id == draft_id).first()
    if not draft:
        raise HTTPException(status_code=404, detail="Draft not found")
    draft.status = "rejected"
    draft.rejection_reason = reason
    db.commit()
    return {"message": f"Draft {draft_id} rejected with reason: {reason}"}
