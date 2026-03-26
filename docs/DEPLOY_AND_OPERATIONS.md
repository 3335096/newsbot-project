# Развертывание и эксплуатация

## 1. Быстрый запуск (Docker Compose)

1. Скопируйте переменные окружения:
   - `cp .env.example .env`
2. Проверьте ключевые значения в `.env`:
   - `DATABASE_URL`
   - `TELEGRAM_BOT_TOKEN`
   - `TELEGRAM_ADMIN_IDS`
   - `TELEGRAM_ALLOWED_USER_IDS`
   - `OPENROUTER_API_KEY`
3. Запустите сервисы:
   - `docker compose up --build`

Состав сервисов:
- `api` — FastAPI
- `bot` — Telegram bot
- `worker` — RQ worker для фоновых задач
- `redis` — брокер очередей
- `db` — PostgreSQL

## 2. Локальный запуск без Docker

1. Установите зависимости:
   - `python3 -m pip install -r requirements.txt`
2. Примените миграции:
   - `alembic upgrade head`
3. Запустите API:
   - `uvicorn app.main:app --host 0.0.0.0 --port 8000`
4. Запустите бота (выберите режим):
   - polling (локальная разработка): `python -m bot.main`
   - webhook (production): запуск бота как отдельного polling-процесса не нужен, апдейты приходят в API `POST /bot/webhook`
5. Запустите worker:
   - `python -m worker`

## 3. Проверка после деплоя (smoke-check)

- Импорт API:
  - `python3 -c "import app.main; print('import app.main: OK')"`
- Импорт бота:
  - `python3 -c "import bot.main; print('import bot.main: OK')"`
- Проверка SQL миграций:
  - `alembic upgrade head --sql`

## 3.1. Webhook-режим Telegram (Iteration 17/18)

- Включение режима:
  - `TELEGRAM_USE_WEBHOOK=true`
- Секрет заголовка:
  - `TELEGRAM_WEBHOOK_SECRET=<strong-random-token>`
- Admin token для webhook-операций:
  - `WEBHOOK_ADMIN_TOKEN=<strong-random-token>`
- Полный URL webhook:
  - `TELEGRAM_WEBHOOK_URL=https://<your-domain>/bot/webhook`
- Endpoint:
  - `POST /bot/webhook`
  - проверяется заголовок `X-Telegram-Bot-Api-Secret-Token` (если секрет задан)
  - `GET /bot/webhook/info` (требует `X-Webhook-Admin-Token`, если `WEBHOOK_ADMIN_TOKEN` задан)
  - `POST /bot/webhook/set` (требует `X-Webhook-Admin-Token`, если `WEBHOOK_ADMIN_TOKEN` задан)
  - `POST /bot/webhook/delete` (требует `X-Webhook-Admin-Token`, если `WEBHOOK_ADMIN_TOKEN` задан)
- В polling-режиме (`TELEGRAM_USE_WEBHOOK=false`) бот продолжает работать через `python -m bot.main`.

Webhook operations API:
- `GET /bot/webhook/info` — получить текущий webhook info из Telegram.
- `POST /bot/webhook/set` — установить webhook:
  - body: `url` (optional, fallback к `TELEGRAM_WEBHOOK_URL`), `secret_token` (optional), `drop_pending_updates` (optional).
- `POST /bot/webhook/delete` — удалить webhook:
  - query: `drop_pending_updates` (optional).

Пример установки webhook через Bot API:

```bash
curl -X POST "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/setWebhook" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://<your-domain>/bot/webhook",
    "secret_token": "'"${TELEGRAM_WEBHOOK_SECRET}"'"
  }'
```

## 4. Логи и диагностика

- API/бот используют стандартный лог-вывод процесса.
- Ключевые точки для диагностики:
  - ошибки LLM запросов (OpenRouter),
  - ошибки миграций,
  - ошибки обработки callback в боте,
  - ошибки RQ worker/Redis (очереди `llm`, `publications`).
- Метрики Prometheus доступны по endpoint:
  - `GET /metrics`
  - формат: `text/plain; version=0.0.4` (prometheus-client)

### Очереди и асинхронные задачи (Iteration 8/10)

- Брокер: Redis (`REDIS_URL`)
- Очереди:
  - `QUEUE_LLM_NAME` (по умолчанию `llm`)
  - `QUEUE_PUBLICATIONS_NAME` (по умолчанию `publications`)
  - `QUEUE_FAILED_NAME` (по умолчанию `failed`)
- Worker:
  - `python -m worker`
- Retry:
  - на уровне RQ (`QUEUE_JOB_RETRIES`)
  - интервалы retry задаются в приложении (5s, 15s, 30s).
- Worker heartbeat:
  - `WORKER_HEARTBEAT_TTL_SECONDS`
  - endpoint-ы health/queue используют heartbeat для статуса worker.

### Reliability и queue operations (Iteration 10)

- Queue observability API:
  - `GET /api/queue/stats`
- Ручной requeue failed jobs:
  - `POST /api/queue/failed/{job_id}/requeue`
- Дополнительные health endpoints:
  - `GET /health/ready`
  - `GET /health/live`
- При фатальных ошибках job marker добавляется в `failed` queue для операционного requeue.

### Что мониторить в первую очередь

- HTTP API:
  - `newsbot_http_requests_total`
  - `newsbot_http_request_duration_seconds`
- Pipeline парсинга:
  - `newsbot_parser_events_total` (`processed`, `created`, `drafts_created`, `blocked`, `flagged`)
- LLM:
  - `newsbot_llm_tasks_total` (по `task_type` и `status`)
- Публикации:
  - `newsbot_publication_events_total`
  - `newsbot_publication_messages_sent_total`
- Scheduler:
  - `newsbot_scheduler_job_runs_total`
  - `newsbot_scheduler_job_duration_seconds`

### Управление источниками (Iteration 9)

- API управления источниками:
  - `GET /api/sources`
  - `GET /api/sources/{id}`
  - `POST /api/sources`
  - `PUT /api/sources/{id}`
  - `DELETE /api/sources/{id}`
  - `POST /api/sources/{id}/parse-now`
- Cron-выражения валидируются на этапе create/update.
- При изменении источника (`enabled`/`schedule_cron`) scheduler автоматически
  синхронизирует job `fetch_source_{id}`.

### Auto-sync webhook режима на старте API (Iteration 20)

На startup API выполняется синхронизация webhook режима:
- `TELEGRAM_WEBHOOK_AUTOSYNC_ON_STARTUP=true`:
  - если `TELEGRAM_USE_WEBHOOK=true`:
    - выполняется `setWebhook` на `TELEGRAM_WEBHOOK_URL`,
    - `secret_token` берется из `TELEGRAM_WEBHOOK_SECRET` (если задан),
    - при `TELEGRAM_WEBHOOK_DROP_PENDING_ON_SET=true` предварительно выполняется delete webhook с `drop_pending_updates=true`.
  - если `TELEGRAM_USE_WEBHOOK=false`:
    - webhook удаляется (`deleteWebhook`),
    - `drop_pending_updates` контролируется `TELEGRAM_WEBHOOK_DROP_PENDING_ON_DISABLE`.
- `TELEGRAM_WEBHOOK_AUTOSYNC_ON_STARTUP=false`:
  - авто-синхронизация отключена, режим управляется вручную через `/bot/webhook/set|delete`.

## 5. Управление доступом

- Белый список:
  - `TELEGRAM_ALLOWED_USER_IDS`
- Админы:
  - `TELEGRAM_ADMIN_IDS`
- Если `TELEGRAM_ALLOWED_USER_IDS` пуст, используется `TELEGRAM_ADMIN_IDS`.

## 6. Рекомендации по эксплуатации

- Не хранить секреты в репозитории.
- Перед обновлениями на проде:
  1. `alembic upgrade head --sql`
  2. `alembic upgrade head`
  3. smoke-check импортов.
- После каждой новой итерации обновлять:
  - `docs/ITERATIONS_LOG.md`
  - при необходимости `README.md`.
