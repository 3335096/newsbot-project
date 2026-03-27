import asyncio
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


async def _run_startup_step(name: str, coro, timeout_seconds: float = 20.0):
    try:
        return await asyncio.wait_for(coro, timeout=timeout_seconds)
    except asyncio.TimeoutError:
        logger.warning("{} timed out after {}s; continuing startup", name, timeout_seconds)
    except Exception as exc:
        logger.exception("{} failed: {}", name, exc)
    return None


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting up...")
    await _run_startup_step("ensure_bot_commands", ensure_bot_commands(), timeout_seconds=20.0)
    sync_result = await _run_startup_step(
        "sync_webhook_mode",
        sync_webhook_mode(),
        timeout_seconds=20.0,
    )
    try:
        if sync_result is not None:
            logger.info("Webhook autosync result: {}", sync_result)
    except Exception:
        # Logging should never break startup.
        pass
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

