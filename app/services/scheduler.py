from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from loguru import logger
import time
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.metrics import record_scheduler_job
from app.db.models.source import Source
from app.db.session import SessionLocal
from app.services.parser_service import ParserService
from app.services.queue_dispatcher import enqueue_due_publications

class Scheduler:
    def __init__(self):
        self.scheduler = AsyncIOScheduler()
        self.parser_service = ParserService()

    def start(self):
        self.scheduler.start()
        logger.info("Scheduler started")

    def add_job(self, func, trigger, id, **kwargs):
        self.scheduler.add_job(func, trigger, id=id, **kwargs)
        logger.info(f"Added job {id}")

    def remove_source_job(self, source_id: int) -> None:
        job_id = f"fetch_source_{source_id}"
        try:
            self.scheduler.remove_job(job_id)
            logger.info("Removed source job {}", job_id)
        except Exception:
            # It's okay if the job does not exist.
            logger.debug("Source job {} was not present", job_id)

    def sync_source_job(self, source_id: int, cron_schedule: str | None, enabled: bool) -> None:
        self.remove_source_job(source_id)
        if enabled and cron_schedule:
            self.schedule_source_fetching(source_id, cron_schedule)

    def schedule_source_fetching(self, source_id: int, cron_schedule: str):
        async def fetch_source_job():
            started = time.monotonic()
            status = "success"
            db: Session = SessionLocal()
            try:
                source = db.query(Source).filter(Source.id == source_id, Source.enabled.is_(True)).first()
                if not source:
                    logger.warning("Source {} not found or disabled, skipping", source_id)
                    status = "skipped"
                    return

                stats = await self.parser_service.process_source(db, source)
                logger.info(
                    "Source {} processed: processed={}, created={}, drafts_created={}",
                    source_id,
                    stats["processed"],
                    stats["created"],
                    stats["drafts_created"],
                )
            except Exception as exc:
                status = "error"
                logger.exception("Scheduled parser job failed for source {}: {}", source_id, exc)
            finally:
                record_scheduler_job(
                    job_name="fetch_source",
                    status=status,
                    duration_seconds=time.monotonic() - started,
                )
                db.close()

        self.add_job(
            fetch_source_job,
            CronTrigger.from_crontab(cron_schedule),
            id=f"fetch_source_{source_id}"
        )

    def load_scheduled_jobs(self):
        db: Session = SessionLocal()
        try:
            sources = db.query(Source).filter(Source.enabled.is_(True), Source.schedule_cron.isnot(None)).all()
            for source in sources:
                self.schedule_source_fetching(source.id, source.schedule_cron)
        finally:
            db.close()
        self.schedule_publications_processing()
        self.schedule_cleanup_old_data()

    def schedule_publications_processing(self):
        async def process_publications_job():
            started = time.monotonic()
            status = "success"
            db: Session = SessionLocal()
            try:
                enqueued = enqueue_due_publications(db)
                if enqueued:
                    logger.info("Enqueued due publications: {}", enqueued)
            except Exception as exc:
                status = "error"
                logger.exception("Scheduled publication job failed: {}", exc)
            finally:
                record_scheduler_job(
                    job_name="process_publications",
                    status=status,
                    duration_seconds=time.monotonic() - started,
                )
                db.close()

        self.add_job(
            process_publications_job,
            CronTrigger.from_crontab("*/1 * * * *"),
            id="process_publications",
            replace_existing=True,
            max_instances=1,
        )

    def schedule_cleanup_old_data(self):
        async def cleanup_job():
            started = time.monotonic()
            status = "success"
            db: Session = SessionLocal()
            try:
                # Keep data for last 90 days (MVP requirement).
                db.execute(text("DELETE FROM llm_tasks WHERE created_at < now() - interval '90 days'"))
                db.execute(
                    text(
                        "DELETE FROM publications "
                        "WHERE COALESCE(published_at, scheduled_at) < now() - interval '90 days'"
                    )
                )
                db.execute(text("DELETE FROM articles_draft WHERE created_at < now() - interval '90 days'"))
                db.execute(text("DELETE FROM articles_raw WHERE fetched_at < now() - interval '90 days'"))
                db.commit()
                logger.info("Cleanup job finished")
            except Exception as exc:
                status = "error"
                db.rollback()
                logger.exception("Cleanup job failed: {}", exc)
            finally:
                record_scheduler_job(
                    job_name="cleanup_old_data",
                    status=status,
                    duration_seconds=time.monotonic() - started,
                )
                db.close()

        self.add_job(
            cleanup_job,
            CronTrigger.from_crontab("0 3 * * *"),
            id="cleanup_old_data",
            replace_existing=True,
            max_instances=1,
        )

scheduler = Scheduler()
