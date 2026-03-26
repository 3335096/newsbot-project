from __future__ import annotations

from apscheduler.triggers.cron import CronTrigger
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.db.models.source import Source
from app.db.session import get_db
from app.services.parser_service import ParserService
from app.services.scheduler import scheduler

router = APIRouter(prefix="/sources", tags=["sources"])


class SourceOut(BaseModel):
    id: int
    name: str
    type: str
    url: str
    enabled: bool
    schedule_cron: str | None
    translate_enabled: bool
    default_target_language: str
    extraction_rules: dict | None


class SourceCreatePayload(BaseModel):
    name: str = Field(min_length=1)
    type: str = Field(pattern="^(rss|site)$")
    url: str = Field(min_length=1)
    enabled: bool = True
    schedule_cron: str | None = None
    translate_enabled: bool = True
    default_target_language: str = "ru"
    extraction_rules: dict | None = None


class SourceUpdatePayload(BaseModel):
    name: str | None = Field(default=None, min_length=1)
    type: str | None = Field(default=None, pattern="^(rss|site)$")
    url: str | None = Field(default=None, min_length=1)
    enabled: bool | None = None
    schedule_cron: str | None = None
    translate_enabled: bool | None = None
    default_target_language: str | None = None
    extraction_rules: dict | None = None


class ParseNowOut(BaseModel):
    source_id: int
    status: str
    processed: int
    created: int
    drafts_created: int


def _validate_cron(schedule_cron: str | None) -> None:
    if not schedule_cron:
        return
    try:
        CronTrigger.from_crontab(schedule_cron)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Invalid cron expression: {schedule_cron}") from exc


def _source_to_out(source: Source) -> dict:
    return {
        "id": source.id,
        "name": source.name,
        "type": source.type,
        "url": source.url,
        "enabled": source.enabled,
        "schedule_cron": source.schedule_cron,
        "translate_enabled": source.translate_enabled,
        "default_target_language": source.default_target_language,
        "extraction_rules": source.extraction_rules,
    }


@router.get("", response_model=list[SourceOut])
async def list_sources(db: Session = Depends(get_db)):
    sources = db.query(Source).order_by(Source.id.asc()).all()
    return [_source_to_out(source) for source in sources]


@router.get("/{source_id}", response_model=SourceOut)
async def get_source(source_id: int, db: Session = Depends(get_db)):
    source = db.query(Source).filter(Source.id == source_id).first()
    if not source:
        raise HTTPException(status_code=404, detail="Source not found")
    return _source_to_out(source)


@router.post("", response_model=SourceOut)
async def create_source(payload: SourceCreatePayload, db: Session = Depends(get_db)):
    _validate_cron(payload.schedule_cron)

    source = Source(
        name=payload.name.strip(),
        type=payload.type,
        url=payload.url.strip(),
        enabled=payload.enabled,
        schedule_cron=payload.schedule_cron,
        translate_enabled=payload.translate_enabled,
        default_target_language=(payload.default_target_language or "ru").strip(),
        extraction_rules=payload.extraction_rules,
    )
    db.add(source)
    db.commit()
    db.refresh(source)
    scheduler.sync_source_job(source.id, source.schedule_cron, source.enabled)
    return _source_to_out(source)


@router.put("/{source_id}", response_model=SourceOut)
async def update_source(source_id: int, payload: SourceUpdatePayload, db: Session = Depends(get_db)):
    source = db.query(Source).filter(Source.id == source_id).first()
    if not source:
        raise HTTPException(status_code=404, detail="Source not found")

    if payload.name is not None:
        source.name = payload.name.strip()
    if payload.type is not None:
        source.type = payload.type
    if payload.url is not None:
        source.url = payload.url.strip()
    if payload.enabled is not None:
        source.enabled = payload.enabled
    if payload.schedule_cron is not None:
        _validate_cron(payload.schedule_cron)
        source.schedule_cron = payload.schedule_cron
    if payload.translate_enabled is not None:
        source.translate_enabled = payload.translate_enabled
    if payload.default_target_language is not None:
        source.default_target_language = payload.default_target_language.strip() or "ru"
    if payload.extraction_rules is not None:
        source.extraction_rules = payload.extraction_rules

    db.commit()
    db.refresh(source)
    scheduler.sync_source_job(source.id, source.schedule_cron, source.enabled)
    return _source_to_out(source)


@router.delete("/{source_id}")
async def delete_source(source_id: int, db: Session = Depends(get_db)):
    source = db.query(Source).filter(Source.id == source_id).first()
    if not source:
        raise HTTPException(status_code=404, detail="Source not found")
    scheduler.remove_source_job(source.id)
    db.delete(source)
    db.commit()
    return {"status": "deleted", "source_id": source_id}


@router.post("/{source_id}/parse-now", response_model=ParseNowOut)
async def parse_source_now(source_id: int, db: Session = Depends(get_db)):
    source = db.query(Source).filter(Source.id == source_id).first()
    if not source:
        raise HTTPException(status_code=404, detail="Source not found")
    if not source.enabled:
        raise HTTPException(status_code=409, detail="Source is disabled")

    parser = ParserService()
    stats = await parser.process_source(db, source)
    return {
        "source_id": source.id,
        "status": "ok",
        "processed": stats["processed"],
        "created": stats["created"],
        "drafts_created": stats["drafts_created"],
    }
