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

---

## Публикации (`/api/publications`)

### `POST /api/publications`

Создание публикации. При `publish_now=true` публикация ставится в очередь worker-а.

### `GET /api/publications/{publication_id}`

Получение статуса публикации.

### `POST /api/publications/{publication_id}/retry`

Повторная постановка публикации в очередь (для `error`/`queued`/`scheduled`).

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

Placeholder endpoint для webhook-интеграции (будет расширяться в следующих итерациях).
