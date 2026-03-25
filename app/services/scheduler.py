from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from loguru import logger
from sqlalchemy.orm import Session
from app.db.models.source import Source
from app.db.session import SessionLocal

class Scheduler:
    def __init__(self):
        self.scheduler = AsyncIOScheduler()

    def start(self):
        self.scheduler.start()
        logger.info("Scheduler started")

    def add_job(self, func, trigger, id, **kwargs):
        self.scheduler.add_job(func, trigger, id=id, **kwargs)
        logger.info(f"Added job {id}")

    def schedule_source_fetching(self, source_id: int, cron_schedule: str):
        # This is a placeholder. In a real app, func would be an actual fetching function.
        async def fetch_source_job():
            logger.info(f"Fetching source {source_id}...")
            # Here you would call your parser service to fetch and process articles

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
