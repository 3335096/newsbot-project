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
4. Запустите бота:
   - `python -m bot.main`
5. Запустите worker:
   - `python -m worker`

## 3. Проверка после деплоя (smoke-check)

- Импорт API:
  - `python3 -c "import app.main; print('import app.main: OK')"`
- Импорт бота:
  - `python3 -c "import bot.main; print('import bot.main: OK')"`
- Проверка SQL миграций:
  - `alembic upgrade head --sql`

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

### Очереди и асинхронные задачи (Iteration 8)

- Брокер: Redis (`REDIS_URL`)
- Очереди:
  - `QUEUE_LLM_NAME` (по умолчанию `llm`)
  - `QUEUE_PUBLICATIONS_NAME` (по умолчанию `publications`)
- Worker:
  - `python -m worker`
- Retry:
  - на уровне RQ (`QUEUE_JOB_RETRIES`)
  - интервалы retry задаются в приложении (5s, 15s, 30s).

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
