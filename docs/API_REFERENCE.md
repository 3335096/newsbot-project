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

Запуск LLM-задачи для черновика.

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
  "status": "success",
  "result": "...",
  "error": null
}
```

---

## Bot webhook

### `POST /bot/webhook`

Placeholder endpoint для webhook-интеграции (будет расширяться в следующих итерациях).
