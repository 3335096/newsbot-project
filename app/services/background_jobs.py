from __future__ import annotations

import asyncio

from aiogram import Bot
from loguru import logger

from app.db.models.llm_task import LLMTask
from app.db.models.publication import Publication
from app.db.session import SessionLocal
from app.metrics import record_llm_task, record_publication_event
from app.queue import get_failed_queue
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
            failed_job_id = task.queue_job_id
            task.status = "error"
            task.queue_job_id = None
            task.error = str(exc)
            db.commit()
            _move_task_to_failed_queue(failed_job_id)
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

        publication.status = "running"
        db.commit()
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
            failed_job_id = publication.queue_job_id
            publication.status = "error"
            publication.queue_job_id = None
            publication.log = str(exc)
            db.commit()
            _move_task_to_failed_queue(failed_job_id)
        record_publication_event(event="job_processed", status="error")
    finally:
        try:
            asyncio.run(bot.session.close())
        except Exception:
            logger.debug("Failed to close bot session for publication job {}", publication_id)
        db.close()


def _move_task_to_failed_queue(job_id: str | None) -> None:
    if not job_id:
        return
    try:
        failed_queue = get_failed_queue()
        failed_queue.enqueue(
            "app.services.background_jobs._noop_failed_job",
            job_id,
            job_id=f"failed_{job_id}",
            result_ttl=settings.QUEUE_RESULT_TTL_SECONDS,
        )
    except Exception as exc:  # pragma: no cover - best effort only
        logger.debug("Failed to move job {} to failed queue: {}", job_id, exc)


def _noop_failed_job(original_job_id: str) -> None:
    # Marker job in dedicated failed queue to simplify operator requeue flows.
    logger.info("Failed queue marker created for job {}", original_job_id)
