from fastapi import FastAPI
from app.api.routers import bot_webhook, drafts, health, llm
from app.services.scheduler import scheduler
from loguru import logger

app = FastAPI()

app.include_router(health.router)
app.include_router(drafts.router, prefix="/api")
app.include_router(llm.router, prefix="/api")
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
