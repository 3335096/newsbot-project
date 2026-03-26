import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from loguru import logger

from app.api.routers import (
    bot_webhook,
    drafts,
    health,
    llm,
    metrics,
    moderation,
    publications,
    queue_admin,
    sources,
    users,
)
from app.metrics import observe_http_request
from app.services.scheduler import scheduler
from bot.runtime import close_bot_session, ensure_bot_commands, sync_webhook_mode


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting up...")
    await ensure_bot_commands()
    try:
        sync_result = await sync_webhook_mode()
        logger.info("Webhook autosync result: {}", sync_result)
    except Exception as exc:
        logger.exception("Webhook autosync failed: {}", exc)
    scheduler.start()
    scheduler.load_scheduled_jobs()
    try:
        yield
    finally:
        logger.info("Shutting down...")
        await close_bot_session()
        scheduler.scheduler.shutdown()


app = FastAPI(lifespan=lifespan)

app.include_router(health.router)
app.include_router(drafts.router, prefix="/api")
app.include_router(llm.router, prefix="/api")
app.include_router(moderation.router, prefix="/api")
app.include_router(publications.router, prefix="/api")
app.include_router(sources.router, prefix="/api")
app.include_router(queue_admin.router, prefix="/api")
app.include_router(users.router, prefix="/api")
app.include_router(metrics.router)
app.include_router(bot_webhook.router)


@app.middleware("http")
async def prometheus_middleware(request: Request, call_next):
    started = time.monotonic()
    response = await call_next(request)
    observe_http_request(
        method=request.method,
        path=request.url.path,
        status_code=response.status_code,
        duration_seconds=time.monotonic() - started,
    )
    return response

