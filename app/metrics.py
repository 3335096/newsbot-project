from __future__ import annotations

from prometheus_client import Counter, Histogram

HTTP_REQUESTS_TOTAL = Counter(
    "newsbot_http_requests_total",
    "Total HTTP requests processed by API.",
    ["method", "path", "status"],
)

HTTP_REQUEST_DURATION_SECONDS = Histogram(
    "newsbot_http_request_duration_seconds",
    "HTTP request duration in seconds.",
    ["method", "path"],
)

PARSER_EVENTS_TOTAL = Counter(
    "newsbot_parser_events_total",
    "Parser pipeline events.",
    ["event"],
)

LLM_TASKS_TOTAL = Counter(
    "newsbot_llm_tasks_total",
    "LLM task executions by task type and status.",
    ["task_type", "status"],
)

PUBLICATION_EVENTS_TOTAL = Counter(
    "newsbot_publication_events_total",
    "Publication lifecycle events.",
    ["event", "status"],
)

PUBLICATION_MESSAGES_SENT_TOTAL = Counter(
    "newsbot_publication_messages_sent_total",
    "Number of Telegram messages sent during publications.",
)

SCHEDULER_JOB_RUNS_TOTAL = Counter(
    "newsbot_scheduler_job_runs_total",
    "Scheduler job runs by job and status.",
    ["job_name", "status"],
)

SCHEDULER_JOB_DURATION_SECONDS = Histogram(
    "newsbot_scheduler_job_duration_seconds",
    "Scheduler job duration in seconds.",
    ["job_name"],
)

QUEUE_EVENTS_TOTAL = Counter(
    "newsbot_queue_events_total",
    "Queue operational events.",
    ["event", "queue_name"],
)

QUEUE_DEPTH = Histogram(
    "newsbot_queue_depth",
    "Observed queue depth samples.",
    ["queue_name"],
)


def observe_http_request(method: str, path: str, status_code: int, duration_seconds: float) -> None:
    method_label = (method or "UNKNOWN").upper()
    path_label = path or "unknown"
    status_label = str(status_code)

    HTTP_REQUESTS_TOTAL.labels(
        method=method_label,
        path=path_label,
        status=status_label,
    ).inc()
    HTTP_REQUEST_DURATION_SECONDS.labels(
        method=method_label,
        path=path_label,
    ).observe(max(duration_seconds, 0.0))


def record_parser_stats(
    *,
    processed: int = 0,
    created: int = 0,
    drafts_created: int = 0,
    blocked: int = 0,
    flagged: int = 0,
) -> None:
    if processed > 0:
        PARSER_EVENTS_TOTAL.labels(event="processed").inc(processed)
    if created > 0:
        PARSER_EVENTS_TOTAL.labels(event="created").inc(created)
    if drafts_created > 0:
        PARSER_EVENTS_TOTAL.labels(event="drafts_created").inc(drafts_created)
    if blocked > 0:
        PARSER_EVENTS_TOTAL.labels(event="blocked").inc(blocked)
    if flagged > 0:
        PARSER_EVENTS_TOTAL.labels(event="flagged").inc(flagged)


def record_llm_task(task_type: str, status: str) -> None:
    LLM_TASKS_TOTAL.labels(
        task_type=task_type or "unknown",
        status=status or "unknown",
    ).inc()


def record_publication_event(event: str, status: str, sent_messages: int = 0) -> None:
    PUBLICATION_EVENTS_TOTAL.labels(
        event=event or "unknown",
        status=status or "unknown",
    ).inc()
    if sent_messages > 0:
        PUBLICATION_MESSAGES_SENT_TOTAL.inc(sent_messages)


def record_scheduler_job(job_name: str, status: str, duration_seconds: float) -> None:
    job_label = job_name or "unknown"
    status_label = status or "unknown"
    SCHEDULER_JOB_RUNS_TOTAL.labels(job_name=job_label, status=status_label).inc()
    SCHEDULER_JOB_DURATION_SECONDS.labels(job_name=job_label).observe(max(duration_seconds, 0.0))


def record_queue_event(event: str, queue_name: str) -> None:
    QUEUE_EVENTS_TOTAL.labels(
        event=event or "unknown",
        queue_name=queue_name or "unknown",
    ).inc()


def observe_queue_depth(queue_name: str, depth: int) -> None:
    QUEUE_DEPTH.labels(queue_name=queue_name or "unknown").observe(max(depth, 0))
