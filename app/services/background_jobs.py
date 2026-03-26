from __future__ import annotations

import asyncio

from aiogram import Bot
from loguru import logger

from app.db.models.llm_task import LLMTask
from app.db.models.publication import Publication
from app.db.session import SessionLocal
from app.metrics import record_llm_task, record_publication_event
from app.services.llm_task_service import LLMTaskService
from app.services.publisher_service import PublisherService
from core.config import settings


def run_llm_task_job(
    llm_task_id: int,
    *,
    draft_id: int,
    task_type: str,
    preset_name: str,
    model: str | None,
    max_len: int,
) -> None:
    db = SessionLocal()
    try:
        task = db.query(LLMTask).filter(LLMTask.id == llm_task_id).first()
        if not task:
            logger.warning("LLM task {} not found in DB before execution", llm_task_id)
            return

        task.status = "running"
        task.error = None
        db.commit()
        record_llm_task(task_type=task_type, status="running")

        service = LLMTaskService()
        asyncio.run(
            service.run_task(
                db,
                draft_id=draft_id,
                task_type=task_type,
                preset_name=preset_name,
                model=model,
                max_len=max_len,
                existing_task=task,
            )
        )
    except Exception as exc:  # pragma: no cover - background worker path
        logger.exception("LLM background job failed task_id={}: {}", llm_task_id, exc)
        task = db.query(LLMTask).filter(LLMTask.id == llm_task_id).first()
        if task:
            task.status = "error"
            task.queue_job_id = None
            task.error = str(exc)
            db.commit()
        record_llm_task(task_type=task_type, status="error")
    finally:
        db.close()


def process_publication_job(publication_id: int) -> None:
    db = SessionLocal()
    bot = Bot(token=settings.TELEGRAM_BOT_TOKEN)
    try:
        publication = db.query(Publication).filter(Publication.id == publication_id).first()
        if not publication:
            logger.warning("Publication {} not found in DB before execution", publication_id)
            return

        publisher = PublisherService(bot)
        result = asyncio.run(publisher.process_publication(db, publication))
        record_publication_event(
            event="job_processed",
            status=result.publication.status,
            sent_messages=len(result.sent_message_ids),
        )
    except Exception as exc:  # pragma: no cover - background worker path
        logger.exception("Publication background job failed publication_id={}: {}", publication_id, exc)
        publication = db.query(Publication).filter(Publication.id == publication_id).first()
        if publication:
            publication.status = "error"
            publication.queue_job_id = None
            publication.log = str(exc)
            db.commit()
        record_publication_event(event="job_processed", status="error")
    finally:
        try:
            asyncio.run(bot.session.close())
        except Exception:
            logger.debug("Failed to close bot session for publication job {}", publication_id)
        db.close()
