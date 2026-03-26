import time

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
    sources,
)
from app.metrics import observe_http_request
from app.services.scheduler import scheduler

app = FastAPI()

app.include_router(health.router)
app.include_router(drafts.router, prefix="/api")
app.include_router(llm.router, prefix="/api")
app.include_router(moderation.router, prefix="/api")
app.include_router(publications.router, prefix="/api")
app.include_router(sources.router, prefix="/api")
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

@app.on_event("startup")
async def startup_event():
    logger.info("Starting up...")
    scheduler.start()
    scheduler.load_scheduled_jobs()

@app.on_event("shutdown")
async def shutdown_event():
    logger.info("Shutting down...")
    scheduler.scheduler.shutdown()
