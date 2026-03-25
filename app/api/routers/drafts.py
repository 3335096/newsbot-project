from typing import List, Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db.models.article_raw import ArticleRaw
from app.db.session import get_db
from app.db.models.article_draft import ArticleDraft

router = APIRouter()

class DraftRejectPayload(BaseModel):
    reason: str


class DraftOut(BaseModel):
    id: int
    article_raw_id: int | None
    target_language: str
    title_original: str | None
    content_original: str | None
    title_translated: str | None
    content_translated: str | None
    source_language: str | None
    status: Literal["new", "flagged", "approved", "rejected", "published"]


@router.get("/drafts", response_model=List[DraftOut])
async def get_drafts(db: Session = Depends(get_db)):
    drafts = db.query(ArticleDraft).all()
    raw_ids = [d.article_raw_id for d in drafts if d.article_raw_id]
    raw_map = {}
    if raw_ids:
        raws = db.query(ArticleRaw).filter(ArticleRaw.id.in_(raw_ids)).all()
        raw_map = {raw.id: raw for raw in raws}

    result: list[dict] = []
    for draft in drafts:
        title_original = None
        content_original = None
        source_language = None
        if draft.article_raw_id:
            raw = raw_map.get(draft.article_raw_id)
            if raw:
                title_original = raw.title_raw
                content_original = raw.content_raw
                source_language = raw.language_detected

        result.append(
            {
                "id": draft.id,
                "article_raw_id": draft.article_raw_id,
                "target_language": draft.target_language,
                "title_original": title_original,
                "content_original": content_original,
                "title_translated": draft.title_translated,
                "content_translated": draft.content_translated,
                "source_language": source_language,
                "status": draft.status,
            }
        )
    return result


@router.get("/drafts/{draft_id}", response_model=DraftOut)
async def get_draft(draft_id: int, db: Session = Depends(get_db)):
    draft = db.query(ArticleDraft).filter(ArticleDraft.id == draft_id).first()
    if not draft:
        raise HTTPException(status_code=404, detail="Draft not found")

    raw = None
    if draft.article_raw_id:
        raw = db.query(ArticleRaw).filter(ArticleRaw.id == draft.article_raw_id).first()

    return {
        "id": draft.id,
        "article_raw_id": draft.article_raw_id,
        "target_language": draft.target_language,
        "title_original": raw.title_raw if raw else None,
        "content_original": raw.content_raw if raw else None,
        "title_translated": draft.title_translated,
        "content_translated": draft.content_translated,
        "source_language": raw.language_detected if raw else None,
        "status": draft.status,
    }

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
