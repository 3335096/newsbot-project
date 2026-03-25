from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from aiogram import Bot
from loguru import logger
from sqlalchemy.orm import Session
from app.db.models.source import Source
from app.db.session import SessionLocal
from app.services.parser_service import ParserService
from app.services.publisher_service import PublisherService
from core.config import settings

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
                source = db.query(Source).filter(Source.id == source_id, Source.enabled.is_(True)).first()
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
            sources = db.query(Source).filter(Source.enabled.is_(True), Source.schedule_cron.isnot(None)).all()
            for source in sources:
                self.schedule_source_fetching(source.id, source.schedule_cron)
        finally:
            db.close()
        self.schedule_publications_processing()

    def schedule_publications_processing(self):
        async def process_publications_job():
            db: Session = SessionLocal()
            bot = Bot(token=settings.TELEGRAM_BOT_TOKEN)
            publisher = PublisherService(bot)
            try:
                processed = await publisher.process_due_publications(db)
                if processed:
                    logger.info("Processed due publications: {}", processed)
            except Exception as exc:
                logger.exception("Scheduled publication job failed: {}", exc)
            finally:
                await bot.session.close()
                db.close()

        self.add_job(
            process_publications_job,
            CronTrigger.from_crontab("*/1 * * * *"),
            id="process_publications",
            replace_existing=True,
            max_instances=1,
        )

scheduler = Scheduler()
