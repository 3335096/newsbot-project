from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from loguru import logger
from sqlalchemy.orm import Session
from app.db.models.source import Source
from app.db.session import SessionLocal
from app.services.parser_service import ParserService

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

    def schedule_source_fetching(self, source_id: int, cron_schedule: str):
        async def fetch_source_job():
            db: Session = SessionLocal()
            try:
                source = db.query(Source).filter(Source.id == source_id, Source.enabled == True).first()
                if not source:
                    logger.warning("Source {} not found or disabled, skipping", source_id)
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
                logger.exception("Scheduled parser job failed for source {}: {}", source_id, exc)
            finally:
                db.close()

        self.add_job(
            fetch_source_job,
            CronTrigger.from_crontab(cron_schedule),
            id=f"fetch_source_{source_id}"
        )

    def load_scheduled_jobs(self):
        db: Session = SessionLocal()
        try:
            sources = db.query(Source).filter(Source.enabled == True, Source.schedule_cron.isnot(None)).all()
            for source in sources:
                self.schedule_source_fetching(source.id, source.schedule_cron)
        finally:
            db.close()

scheduler = Scheduler()
