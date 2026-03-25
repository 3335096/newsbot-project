from fastapi import FastAPI
from loguru import logger

from app.api.routers import bot_webhook, drafts, health, llm, publications
from app.services.scheduler import scheduler

app = FastAPI()

app.include_router(health.router)
app.include_router(drafts.router, prefix="/api")
app.include_router(llm.router, prefix="/api")
app.include_router(publications.router, prefix="/api")
app.include_router(bot_webhook.router)

@app.on_event("startup")
async def startup_event():
    logger.info("Starting up...")
    scheduler.start()
    scheduler.load_scheduled_jobs()

@app.on_event("shutdown")
async def shutdown_event():
    logger.info("Shutting down...")
    scheduler.scheduler.shutdown()
