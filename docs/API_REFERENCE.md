# API Reference (MVP)

Базовый URL API:

- локально: `http://localhost:8000`
- внутри docker-compose (для бота): `http://api:8000`

## Health

### `GET /health`

Проверка работоспособности сервиса.

**Ответ:**

```json
{
  "status": "ok"
}
```

### `GET /health/ready`

Readiness endpoint для проверки готовности async-контура:
- доступность Redis (`redis.ok`)
- состояние worker heartbeat (`worker.alive`, `worker.last_seen`)
- краткая статистика очередей (`llm`, `publications`, `failed`)

Если Redis недоступен, статус становится `degraded`.

### `GET /metrics`

Prometheus-метрики приложения в формате `text/plain; version=0.0.4`.

Примеры метрик:
- `newsbot_http_requests_total`
- `newsbot_http_request_duration_seconds`
- `newsbot_parser_events_total`
- `newsbot_llm_tasks_total`
- `newsbot_publication_events_total`
- `newsbot_publication_messages_sent_total`
- `newsbot_scheduler_job_runs_total`
- `newsbot_scheduler_job_duration_seconds`

---

## Черновики (`/api/drafts`)

### `GET /api/drafts`

Список черновиков с оригиналом и переводом.

**Ответ (пример):**

```json
[
  {
    "id": 1,
    "article_raw_id": 10,
    "target_language": "ru",
    "title_original": "Original title",
    "content_original": "Original text",
    "title_translated": "Переведенный заголовок",
    "content_translated": "Переведенный текст",
    "source_language": "en",
    "status": "new"
  }
]
```

### `GET /api/drafts/{draft_id}`

Карточка одного черновика.

### `POST /api/drafts/{draft_id}/approve`

Переводит черновик в статус `approved`.

### `POST /api/drafts/{draft_id}/reject`

Отклоняет черновик.

**Тело запроса:**

```json
{
  "reason": "Не соответствует редакционной политике"
}
```

---

## LLM Presets и задачи (`/api/llm`)

### `GET /api/llm/presets`

Список пресетов LLM.

### `POST /api/llm/presets/{preset_name}`

Обновление пресета.

**Тело запроса (любая комбинация полей):**

```json
{
  "system_prompt": "Новый system prompt",
  "user_prompt_template": "Новый шаблон user prompt",
  "default_model": "openai/gpt-4o-mini",
  "enabled": true
}
```

### `POST /api/llm/tasks`

Постановка LLM-задачи для черновика в очередь (асинхронно).

**Тело запроса:**

```json
{
  "draft_id": 1,
  "task_type": "summary",
  "preset": "summary",
  "model": "openai/gpt-4o-mini",
  "max_len": 700
}
```

`task_type`:

- `summary`
- `rewrite`
- `title_hashtags`

**Ответ (пример):**

```json
{
  "id": 22,
  "draft_id": 1,
  "task_type": "summary",
  "preset": "summary",
  "model": "openai/gpt-4o-mini",
  "status": "queued",
  "result": null,
  "error": null
}
```

### `GET /api/llm/tasks/{task_id}`

Получение актуального статуса и результата LLM-задачи.

### `POST /api/llm/tasks/{task_id}/retry`

Повторная постановка завершенной (`success`) или ошибочной (`error`) задачи в очередь.

Если у задачи есть `queue_job_id`, endpoint сначала пытается requeue существующего failed/stopped/canceled job.
Если requeue невозможен — задача ставится заново обычным enqueue.

---

## Публикации (`/api/publications`)

### `POST /api/publications`

Создание публикации. При `publish_now=true` публикация ставится в очередь worker-а.

### `GET /api/publications/{publication_id}`

Получение статуса публикации.

### `POST /api/publications/{publication_id}/retry`

Повторная постановка публикации в очередь (для `error`/`queued`/`scheduled`).

Если у публикации есть `queue_job_id`, endpoint сначала пытается requeue существующего failed/stopped/canceled job.
Если requeue невозможен — публикация ставится заново обычным enqueue.

---

## Queue Admin (`/api/queue`)

### `GET /api/queue/stats`

Операционная статистика очередей:
- `llm`
- `publications`
- `failed`

Возвращает:
- `queued/started/finished/failed/deferred/scheduled` по каждой очереди
- `redis_ok`
- `worker_alive`
- `worker_last_seen_ts`
- `worker_last_seen_iso`

### `POST /api/queue/failed/{job_id}/requeue`

Ручной requeue для job, отмеченной в failed queue marker.

Сценарий:
1. Проверяется marker-job `failed_{job_id}` в failed queue.
2. Проверяется оригинальный job `job_id`.
3. Выполняется requeue оригинального job.
4. Marker удаляется из failed queue.

---

## Источники (`/api/sources`)

### `GET /api/sources`

Список источников (сортировка по `id ASC`).

### `GET /api/sources/{source_id}`

Карточка конкретного источника.

### `POST /api/sources`

Создание источника.

Поддерживаемые поля:
- `name`
- `type` (`rss` | `site`)
- `url`
- `enabled`
- `schedule_cron` (cron-expression в формате crontab)
- `translate_enabled`
- `default_target_language`
- `extraction_rules` (JSON)

При некорректном `schedule_cron` возвращается `400`.

### `PUT /api/sources/{source_id}`

Обновление источника (частичное).

При изменении `enabled`/`schedule_cron` выполняется синхронизация scheduler job:
- job удаляется, если источник выключен или cron пустой,
- job пересоздается, если источник включен и cron валиден.

### `DELETE /api/sources/{source_id}`

Удаление источника.

Перед удалением удаляется связанный scheduler job `fetch_source_{id}`.

### `POST /api/sources/{source_id}/parse-now`

Ручной запуск парсинга источника прямо сейчас.

Ответ:
- `source_id`
- `status`
- `processed`
- `created`
- `drafts_created`

Если источник выключен — `409`.

---

## Bot webhook

### `POST /bot/webhook`

Webhook endpoint для Telegram updates.

Поведение:
- принимает update payload Telegram;
- валидирует payload через `aiogram.types.Update`;
- передает update в общий aiogram dispatcher (`feed_update`);
- возвращает `{"status":"ok"}` при успешной обработке.

Security:
- если задан `TELEGRAM_WEBHOOK_SECRET`, endpoint требует header:
  - `X-Telegram-Bot-Api-Secret-Token: <secret>`
- при несовпадении — `401 Invalid webhook secret`.

### `GET /bot/webhook/info`

Возвращает текущее состояние webhook, полученное из Telegram Bot API.

Admin security:
- endpoint использует unified admin dependency;
- если задан `ADMIN_API_TOKEN`, требуется header:
  - `X-Admin-Api-Token: <token>`;
- fallback: если `ADMIN_API_TOKEN` пуст, используется legacy `WEBHOOK_ADMIN_TOKEN`.

### `POST /bot/webhook/set`

Устанавливает webhook URL в Telegram Bot API.

Тело запроса:

```json
{
  "url": "https://example.com/bot/webhook",
  "secret_token": "optional-secret",
  "drop_pending_updates": false
}
```

- `url` можно не передавать, если заполнен `TELEGRAM_WEBHOOK_URL`.
- `secret_token` можно не передавать, тогда используется `TELEGRAM_WEBHOOK_SECRET`.
- при `drop_pending_updates=true` перед установкой webhook выполняется `deleteWebhook(drop_pending_updates=true)`.

Security:
- если задан `ADMIN_API_TOKEN`, endpoint требует header:
  - `X-Admin-Api-Token: <token>`;
- fallback: если `ADMIN_API_TOKEN` пуст, используется legacy `WEBHOOK_ADMIN_TOKEN`;
- при несовпадении — `401 Invalid admin api token`.

### `POST /bot/webhook/delete`

Удаляет webhook.

Query-параметры:
- `drop_pending_updates` (`false` по умолчанию)

Security:
- если задан `ADMIN_API_TOKEN`, endpoint требует header:
  - `X-Admin-Api-Token: <token>`;
- fallback: если `ADMIN_API_TOKEN` пуст, используется legacy `WEBHOOK_ADMIN_TOKEN`;
- при несовпадении — `401 Invalid admin api token`.

## Admin API auth (Iteration 21)

Unified admin auth dependency применяется к admin/ops endpoint-ам:
- `/api/queue/*`
- `/api/moderation/*`
- `POST /api/llm/presets/{preset_name}`
- `/bot/webhook/info|set|delete`

Заголовок:
- `X-Admin-Api-Token: <token>`

Поведение:
- если `ADMIN_API_TOKEN` пуст, используется fallback к legacy `WEBHOOK_ADMIN_TOKEN`;
- при несовпадении — `401 Invalid admin api token`.
