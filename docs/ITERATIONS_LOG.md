# Журнал выполнения итераций

Этот документ является **основным журналом прогресса** по этапам реализации.
Его нужно обновлять после завершения каждой следующей итерации.

## Правило обновления

После закрытия очередной итерации обязательно:
1. добавить новый раздел `## Итерация N`,
2. зафиксировать:
   - что реализовано,
   - какие файлы изменены,
   - какие проверки выполнены,
   - риски/ограничения и следующий шаг.

---

## Итерация 1 — Скелет проекта и базовая схема

### Что сделано
- Подготовлен базовый каркас backend + bot.
- Приведены SQLAlchemy-модели к MVP-схеме из ТЗ.
- Добавлена инфраструктура Alembic:
  - `alembic.ini`
  - `migrations/env.py`
  - `migrations/script.py.mako`
  - первичная миграция `20260325_0001_init_schema.py`
- Добавлена базовая авторизация бота:
  - whitelist: `TELEGRAM_ALLOWED_USER_IDS`
  - админ-доступ: `TELEGRAM_ADMIN_IDS`
- Добавлены базовые API-маршруты:
  - `GET /health`
  - `GET /api/drafts`
  - `POST /api/drafts/{id}/approve`
  - `POST /api/drafts/{id}/reject`
  - `POST /bot/webhook` (placeholder)

### Проверки
- Синтаксическая валидация модулей Python (`compileall`) — успешно.

---

## Итерация 2 — Парсинг, дедупликация, сохранение raw

### Что сделано
- Реализован `ParserService`:
  - `fetch_rss`
  - `fetch_html`
  - `extract_content`
  - `detect_language`
  - `compute_hash`
  - `upsert_article_raw`
  - `process_source`
- Добавлена дедупликация по:
  - `url`
  - `(source_id, hash_original)`
- Подключен реальный вызов парсера из scheduler-job.

### Тесты
- Добавлены unit-тесты `tests/services/test_parser_service.py`:
  - нормализация и стабильность хеша,
  - детект языка,
  - извлечение по CSS-правилам,
  - дедупликация upsert.

### Проверки
- `pytest tests/services/test_parser_service.py` — успешно.

---

## Итерация 3 — Перевод, кэш переводов, drafts в ленте

### Что сделано
- Обновлен LLM-клиент под OpenRouter chat-completions.
- Реализован `TranslationService`:
  - перевод заголовка и контента,
  - формирование/парсинг ответа модели,
  - `get_or_create_draft_for_article`.
- Реализован кэш переводов (reuse) по:
  - `hash_original`,
  - `target_language`,
  - `model`,
  - `preset`.
- Встроено автосоздание `ArticleDraft` в pipeline парсинга.
- Расширены API и бот для отображения оригинала/перевода:
  - `GET /api/drafts/{id}`
  - переключение вида в карточке бота.

### Тесты и проверки
- Расширены тесты parser-сервиса для сценария translation cache.
- `pytest tests/services/test_parser_service.py` — успешно.

---

## Итерация 4 — LLM-пресеты и редактирование через бота

### Что сделано
- Добавлена модель пресетов `LLMPreset` и миграция `20260325_0002_add_llm_presets`.
- Создан сервис пресетов `LLMPresetService`:
  - bootstrap default-пресетов,
  - список,
  - обновление.
- Создан сервис задач `LLMTaskService`:
  - выполнение задач `summary`, `rewrite`, `title_hashtags`,
  - запись `llm_tasks`,
  - применение результатов к `ArticleDraft`.
- Добавлен API-роутер `/api/llm`:
  - `GET /api/llm/presets`
  - `POST /api/llm/presets/{preset_name}`
  - `POST /api/llm/tasks`
- Добавлены действия в Telegram-боте:
  - карточка draft: Summary / Rewrite style / Title+Hashtags
  - админ-меню пресетов
  - команды редактирования:
    - `/preset_system <preset> <text>`
    - `/preset_user <preset> <text>`

### Проверки
- `pytest tests/services/test_parser_service.py` — успешно.
- Smoke-check:
  - `import app.main` — OK
  - `import bot.main` — OK
  - `alembic upgrade head --sql` — OK

### Особенность миграции
- Для SQLite/offline smoke добавлена безопасная ветка в миграции (без неподдерживаемых операций ALTER constraint).
- Для целевой БД (PostgreSQL) сохранено применение ограничений статуса.

---

## Итерация 5 — Публикация в Telegram-канал, шаблон поста, планирование

### Что сделано
- Реализован расширенный `PublisherService`:
  - формирование поста по шаблону (`заголовок + текст + ссылка на источник`),
  - безопасное форматирование в HTML,
  - разбиение длинных постов под ограничения Telegram,
  - ограничение длины caption для публикации с фото,
  - обработка изображения (если есть) с fallback на текстовую отправку.
- Добавлен workflow публикаций:
  - создание публикации (немедленная или запланированная),
  - обработка очереди публикаций по статусам `queued/scheduled`,
  - фиксация статусов `published/error`,
  - запись `message_id` и лога отправки.
- Добавлены API-эндпоинты публикаций:
  - `POST /api/publications`
  - `GET /api/publications/{id}`
- Интеграция публикации в бота:
  - в карточке черновика появились кнопки `Publish now: <channel>`
    (по списку из `TELEGRAM_CHANNEL_IDS`).
- Интеграция со scheduler:
  - добавлена периодическая задача обработки отложенных публикаций (`*/1 * * * *`).
- Миграция `20260325_0003_publication_status_and_uniques`:
  - нормализация статусов таблицы `publications`,
  - check-constraint на допустимые статусы,
  - уникальность `(draft_id, channel_id)` для идемпотентности публикации
    (в SQLite/offline-safe режиме ограничение пропускается при `--sql`).

### Тесты и проверки
- Добавлены unit-тесты `tests/services/test_publisher_service.py`:
  - рендер поста,
  - разбиение длинного текста,
  - ограничение caption,
  - выбор media URL.
- Запуск тестов:
  - `pytest tests/services/test_parser_service.py tests/services/test_publisher_service.py` — успешно.
- Smoke-check:
  - `import app.main` — OK
  - `import bot.main` — OK
  - `alembic upgrade head --sql` — OK

### Ограничения на текущем шаге
- Для SQLite offline SQL в миграции не выполняются операции, требующие batch reflection.
- Основная целевая среда исполнения и ограничений — PostgreSQL.
