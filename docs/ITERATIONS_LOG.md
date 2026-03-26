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

---

## Итерация 6 — Модерация, правила, статусы и очистка 90 дней

### Что сделано
- Реализован `ModerationService`:
  - оценка статьи по правилам `domain_blacklist` и `keyword_blacklist`,
  - действия правил `block` / `flag`,
  - унифицированная структура `flags` для отображения в карточке.
- Модерация встроена в pipeline парсинга (`ParserService`):
  - модерация выполняется на каждом материале,
  - при `block` материал не попадает в черновики,
  - при `flag` черновик получает статус `flagged`,
  - сработавшие правила сохраняются в `articles_draft.flags`.
- Добавлен API модерации:
  - `GET /api/moderation/rules`
  - `POST /api/moderation/rules`
  - `POST /api/moderation/rules/{id}/toggle`
- Бот (админ):
  - раздел `Moderation Rules` в `/admin`,
  - просмотр правил, toggle через inline,
  - добавление правила командой:
    - `/rule_add <kind> <pattern> <action> [comment]`
- Карточка draft в боте теперь показывает блок `Moderation flags` при наличии сработавших правил.
- Scheduler:
  - добавлена ежедневная очистка данных старше 90 дней (`0 3 * * *`) для:
    - `llm_tasks`
    - `publications`
    - `articles_draft`
    - `articles_raw`
- Добавлена миграция `20260325_0004_moderation_status_constraints`:
  - нормализация `moderation_rules.kind` и `moderation_rules.action`,
  - check-constraints на допустимые значения (с SQLite-safe веткой).

### Тесты и проверки
- Добавлены unit-тесты `tests/services/test_moderation_service.py`:
  - срабатывание keyword/domain правил,
  - block/flag outcomes,
  - create/toggle rule.
- Запуск тестов:
  - `pytest tests/services/test_parser_service.py tests/services/test_publisher_service.py tests/services/test_moderation_service.py` — успешно.
- Smoke-check:
  - `import app.main` — OK
  - `import bot.main` — OK
  - `alembic upgrade head --sql` — OK (до ревизии `20260325_0004`)

### Ограничения на текущем шаге
- В текущем варианте `block` означает пропуск создания/обновления draft, но `articles_raw` всё равно сохраняется.
- Очистка рассчитана под PostgreSQL (`interval`), для SQLite она используется только в smoke-сценариях без фактического выполнения cleanup job.

---

## Итерация 7 — Метрики, UX-полировка и hardening

### Что сделано
- Добавлен Prometheus-мониторинг:
  - новый endpoint `GET /metrics`,
  - HTTP-метрики через middleware (`method/path/status`, длительность),
  - сервисные метрики для parser/LLM/publications/scheduler.
- Вынесен единый модуль метрик `app/metrics.py` с helper-функциями:
  - `observe_http_request`,
  - `record_parser_stats`,
  - `record_llm_task`,
  - `record_publication_event`,
  - `record_scheduler_job`.
- Инструментированы основные pipeline:
  - `ParserService.process_source` (processed/created/drafts_created/blocked/flagged),
  - `LLMTaskService.run_task` (running/success/error),
  - `PublisherService` (создание/пропуск/успех/ошибка публикации + число отправленных сообщений),
  - jobs в `Scheduler` (status и duration по задачам `fetch_source`, `process_publications`, `cleanup_old_data`).
- UX-полировка Telegram-бота:
  - унифицированы сообщения и кнопки на русском,
  - улучшена читаемость карточки черновика и текста ошибок,
  - доработаны подписи меню и админ-панели.
- Добавлены hardening-тесты pipeline модерации:
  - новый файл `tests/services/test_parser_moderation_pipeline.py`,
  - сценарий `block`: черновик не создается, счетчик `blocked` растет,
  - сценарий `flag`: черновик получает `status=flagged`, сохраняются `flags`, растут метрики.

### Измененные файлы (ключевые)
- `app/main.py`
- `app/api/routers/metrics.py`
- `app/api/routers/__init__.py`
- `app/metrics.py`
- `app/services/parser_service.py`
- `app/services/llm_task_service.py`
- `app/services/publisher_service.py`
- `app/services/scheduler.py`
- `bot/handlers/start.py`
- `bot/handlers/drafts.py`
- `bot/handlers/admin.py`
- `bot/keyboards/main_menu.py`
- `tests/services/test_parser_moderation_pipeline.py`
- `docs/API_REFERENCE.md`
- `docs/BOT_GUIDE.md`
- `docs/DEPLOY_AND_OPERATIONS.md`
- `docs/TESTING.md`

### Проверки
- Unit-тесты сервисов (включая новый hardening-набор) — выполняются в рамках Iteration 7.
- Smoke-check (imports + alembic `--sql`) — выполняется в рамках Iteration 7.

### Ограничения на текущем шаге
- Метрики не агрегируют бизнес-сущности по source_id/channel_id (умышленно, чтобы избежать высокой cardinality label-ов).
- Endpoint `/metrics` открыт без auth в рамках MVP и должен защищаться на уровне инфраструктуры (ingress/reverse proxy/private network).

---

## Итерация 8 — Асинхронные очереди (Redis + RQ) для LLM и публикаций

### Что сделано
- Внедрена очередь фоновых задач на базе Redis + RQ:
  - добавлен слой очередей `app/queue.py`,
  - добавлен worker entrypoint `worker.py`,
  - добавлены фоновые job handlers `app/services/background_jobs.py`.
- LLM-задачи переведены в async-поток:
  - `POST /api/llm/tasks` теперь создает `llm_tasks` со статусом `queued` и ставит job в очередь,
  - добавлен endpoint `GET /api/llm/tasks/{task_id}` для проверки статуса/результата,
  - добавлен endpoint `POST /api/llm/tasks/{task_id}/retry` для повторного запуска.
- Публикации переведены в async-поток:
  - `POST /api/publications` при `publish_now=true` ставит публикацию в очередь вместо синхронной отправки,
  - добавлен endpoint `POST /api/publications/{publication_id}/retry`,
  - scheduler теперь enqueue-ит due-публикации (`queued/scheduled`), а не отправляет их синхронно.
- Добавлена идемпотентность очередей на уровне БД:
  - поля `queue_job_id` в `llm_tasks` и `publications`,
  - `channel_alias` в `publications` для сохранения ключа канала.
- Добавлена миграция:
  - `20260325_0005_async_queue_statuses.py`
  - нормализует статусы и добавляет ограничения:
    - `llm_tasks.status IN ('queued','running','success','error')`
    - `publications.status IN ('queued','running','scheduled','success','error')`
    - unique для `queue_job_id`.
- Добавлен тест очередного диспетчера:
  - `tests/services/test_queue_dispatcher.py` (enqueue queued + due scheduled, skip future scheduled).

### Измененные файлы (ключевые)
- `core/config.py`
- `requirements.txt`
- `docker-compose.yml`
- `.env.example`
- `worker.py`
- `app/queue.py`
- `app/services/background_jobs.py`
- `app/services/queue_dispatcher.py`
- `app/services/llm_task_service.py`
- `app/services/publisher_service.py`
- `app/services/scheduler.py`
- `app/api/routers/llm.py`
- `app/api/routers/publications.py`
- `app/db/models/llm_task.py`
- `app/db/models/publication.py`
- `migrations/versions/20260325_0005_async_queue_statuses.py`
- `tests/services/test_queue_dispatcher.py`

### Проверки
- Для Iteration 8 выполняются:
  - unit-тесты сервисов (включая новый тест queue-dispatcher),
  - smoke-check импортов и Alembic SQL generation.

### Ограничения на текущем шаге
- В MVP выбран RQ без отдельного persistent result backend (используется Redis result TTL).
- Управление очередями (dead letter/priority queues) пока не выделено в отдельный админ-интерфейс.

---

## Итерация 9 — Управление источниками (API + bot + ручной trigger)

### Что сделано
- Добавлен API-роутер источников `app/api/routers/sources.py`:
  - `GET /api/sources` — список источников,
  - `GET /api/sources/{id}` — карточка источника,
  - `POST /api/sources` — создание источника,
  - `PUT /api/sources/{id}` — обновление источника,
  - `DELETE /api/sources/{id}` — удаление источника,
  - `POST /api/sources/{id}/parse-now` — ручной запуск парсинга выбранного источника.
- Добавлена валидация cron-расписания при create/update:
  - проверка через `apscheduler.CronTrigger.from_crontab`,
  - при невалидном выражении возвращается `400 Invalid cron expression`.
- Добавлена синхронизация scheduler-job для источников:
  - `Scheduler.sync_source_job(source_id, cron, enabled)` — remove+reschedule,
  - `Scheduler.remove_source_job(source_id)` — удаление job по id `fetch_source_{id}`,
  - вызов sync при create/update/delete источника через API.
- Подключен API sources в FastAPI-приложение:
  - экспорт в `app/api/routers/__init__.py`,
  - `app.include_router(sources.router, prefix="/api")` в `app/main.py`.
- Реализован bot-раздел `Источники`:
  - новый handler `bot/handlers/sources.py`,
  - `show_sources` — просмотр списка источников,
  - `source_parse_now_*` — запуск парсинга вручную из бота,
  - `source_toggle_*` — включение/выключение источника,
  - подключение router в `bot/main.py` и `bot/handlers/__init__.py`.

### Тесты и проверки
- Добавлены API-тесты для источников:
  - `tests/services/test_sources_router.py`,
  - сценарии:
    - reject невалидного cron (`400`),
    - create + parse-now (с моком parser stats),
    - update enabled с проверкой вызова scheduler sync,
    - parse-now для disabled source (`409`).
- Обновлены docs по API/bot/testing/deploy для нового слоя sources.

### Ограничения на текущем шаге
- В bot-интерфейсе управления источниками пока реализованы базовые операции (просмотр, toggle, parse-now); создание/редактирование через FSM-команды будет расширено в следующих шагах.
- Ручной `parse-now` выполняется синхронно в контексте API-запроса и рассчитан на точечные ручные запуски.

---

## Итерация 10 — Надежность очередей и queue observability

### Что сделано
- Добавлен контур наблюдаемости и администрирования очередей:
  - новый роутер `app/api/routers/queue_admin.py`:
    - `GET /api/queue/stats` — сводка по очередям (`llm`, `publications`, `failed`) + Redis/worker status,
    - `POST /api/queue/failed/{job_id}/requeue` — ручной requeue failed job.
  - роутер подключен в `app/main.py` и экспортирован в `app/api/routers/__init__.py`.
- Расширен queue слой `app/queue.py`:
  - поддержка `QUEUE_FAILED_NAME`,
  - `QueueSnapshot` + `queue_snapshot(...)`,
  - `fetch_job(job_id)` для универсального поиска job по Redis.
- Добавлен worker heartbeat:
  - новый модуль `app/services/worker_state.py`,
  - heartbeat хранится в Redis (`newsbot:worker:last_seen`),
  - в `worker.py` запущен фоновый heartbeat thread во время работы worker-а.
- Добавлены readiness/health проверки очередей:
  - `GET /health/ready` теперь возвращает:
    - статус Redis (`redis.ok`),
    - состояние worker (`alive`, `last_seen`),
    - snapshot очередей.
- Усилена обработка отказов job-ов:
  - в `app/services/background_jobs.py` при ошибках создается marker в failed queue,
  - `queue_job_id` очищается у сущностей при fail/success в run-потоке,
  - статусы и ошибки синхронизируются с БД.
- Добавлена безопасная логика requeue:
  - в `app/services/queue_dispatcher.py`:
    - `requeue_job_by_id(job_id)`,
    - `requeue_job_object(job)`,
    - requeue разрешен только для `failed/stopped/canceled`.
- Расширены метрики:
  - `newsbot_queue_events_total{event,queue_name}`,
  - `newsbot_queue_depth{queue_name}` (sampled через histogram),
  - helper-функции `record_queue_event`, `observe_queue_depth` в `app/metrics.py`.
- Обновлен конфиг:
  - `core/config.py`, `.env.example`, `README.md`:
    - `QUEUE_FAILED_NAME`,
    - `WORKER_HEARTBEAT_TTL_SECONDS`.

### Тесты и проверки
- Добавлены тесты надежности очередей:
  - `tests/services/test_queue_reliability.py`:
    - heartbeat в Redis,
    - queue stats с признаком `worker_alive`,
    - отсутствие heartbeat => `worker_alive=False`.
- Добавлены тесты requeue:
  - `tests/services/test_queue_dispatcher_requeue.py`:
    - requeue только для failed-like job status.

### Ограничения на текущем шаге
- DLQ реализован через marker-джобы в `failed` queue (операторский MVP-подход), без отдельной бизнес-таблицы инцидентов.
- API queue admin пока без отдельного auth-слоя и предполагает защиту на уровне сети/ingress.

---

## Итерация 11 — CRUD источников в Telegram-боте (FSM)

### Что сделано
- Расширен bot-раздел `Источники` до CRUD-операций без выхода в API-клиент вручную:
  - добавлена кнопка `Добавить источник`,
  - добавлены действия на карточке источника:
    - `Изменить название`,
    - `Изменить cron`,
    - `Удалить источник`,
    - сохранены `Запустить парсинг сейчас` и `Вкл/выкл источник`.
- Реализован FSM-поток создания источника:
  - `name` -> `type (rss/site)` -> `url` -> `cron|'-'`,
  - валидации на стороне бота:
    - непустое название,
    - тип только `rss|site`,
    - URL должен начинаться с `http://` или `https://`.
- Реализованы FSM-потоки редактирования источника:
  - отдельный сценарий смены названия,
  - отдельный сценарий смены cron (`-` для очистки расписания).
- Добавлена защита FSM message-хендлеров:
  - проверка whitelist в состоянии через `_ensure_allowed_message(...)`,
  - сброс состояния при неавторизованном доступе.
- Улучшена UX-подача раздела:
  - при пустом списке источников бот сразу предлагает создать источник в интерфейсе,
  - при успешных create/update бот возвращает обновленную карточку с актуальными action-кнопками.

### Измененные файлы (ключевые)
- `bot/handlers/sources.py`
- `tests/bot/test_sources_handler_helpers.py`
- `docs/BOT_GUIDE.md`
- `docs/TESTING.md`
- `docs/ITERATIONS_LOG.md`
- `README.md`

### Тесты и проверки
- Добавлен новый тестовый модуль:
  - `tests/bot/test_sources_handler_helpers.py`
  - проверяет формат карточки источника, состав action-кнопок и наличие кнопки создания источника.
- Полный прогон тестов и smoke-check выполняется после pre-test commit в рамках текущей итерации.

### Ограничения на текущем шаге
- В FSM-потоке редактируются только `name` и `schedule_cron`; изменение `type/url/translate settings` останется в API и может быть добавлено отдельным шагом.
- Парсинг/валидация cron остается source-of-truth на API-уровне; бот выполняет только базовые клиентские проверки.

---

## Итерация 12 — FSM-редактирование LLM-пресетов в Telegram-боте

### Что сделано
- Убрано ограничение админ-UX по пресетам, где для редактирования выдавались только command hints:
  - callback `Изменить system prompt` теперь запускает FSM-поток ввода нового текста,
  - callback `Изменить user template` также запускает FSM-поток.
- Добавлена state-модель редактирования пресетов:
  - `PresetEditState.waiting_for_system_prompt`,
  - `PresetEditState.waiting_for_user_template`.
- Реализованы message-хендлеры FSM:
  - принимают новый текст,
  - валидируют непустой ввод,
  - вызывают API `POST /api/llm/presets/{preset_name}`,
  - возвращают подтверждение и action-кнопки пресета,
  - очищают state после успешного обновления.
- Сохранена обратная совместимость:
  - команды `/preset_system` и `/preset_user` продолжают работать как fallback.

### Измененные файлы (ключевые)
- `bot/handlers/admin.py`
- `tests/bot/test_admin_handler_helpers.py`
- `docs/BOT_GUIDE.md`
- `docs/TESTING.md`
- `docs/ITERATIONS_LOG.md`
- `README.md`

### Тесты и проверки
- Добавлен новый тестовый модуль:
  - `tests/bot/test_admin_handler_helpers.py`
  - проверяет состав admin keyboard и callback-структуру preset action keyboard.
- Полный прогон тестов и smoke-check выполняется в рамках итерации после pre-test commit.

### Ограничения на текущем шаге
- FSM-редактирование пресетов реализовано только для текстовых полей (`system_prompt`, `user_prompt_template`).
- Редактирование `default_model` через bot UI пока не добавлено (доступно через API).

---

## Итерация 13 — Управление `default_model` пресетов из admin-бота

### Что сделано
- Расширен bot-admin UX для пресетов:
  - в action-кнопки пресета добавлена кнопка `Изменить default model`.
- Добавлен FSM-сценарий редактирования `default_model`:
  - callback `admin_preset_edit_model_<preset>` переводит в состояние ожидания модели,
  - сообщение с новым значением отправляется в API:
    - `POST /api/llm/presets/{preset_name}` с полем `default_model`,
  - значение `-` поддерживается как сброс к `None` (service default model).
- Добавлен fallback через slash-команду:
  - `/preset_model <preset_name> <default_model|->`.
- Обновлены сообщения подтверждения:
  - после update бот показывает актуальный результат и возвращает action-кнопки пресета.

### Измененные файлы (ключевые)
- `bot/handlers/admin.py`
- `tests/bot/test_admin_handler_helpers.py`
- `docs/BOT_GUIDE.md`
- `docs/TESTING.md`
- `docs/ITERATIONS_LOG.md`
- `README.md`

### Тесты и проверки
- Расширен тест `tests/bot/test_admin_handler_helpers.py`:
  - проверка наличия callback `admin_preset_edit_model_<preset>` в keyboard пресета.
- Полный прогон тестов и smoke-check выполняется после pre-test commit в рамках итерации.

### Ограничения на текущем шаге
- Управление `default_model` выполняется как свободный текст (валидация формата/доступности модели остается на API/LLM-провайдере).
- UI выбора модели из списка доступных провайдеров пока не реализован.

---

## Итерация 14 — Расширенное редактирование источников в Telegram-боте

### Что сделано
- Расширен раздел `Источники` в bot UI beyond `name/cron`:
  - добавлены новые action-кнопки в карточке источника:
    - `Изменить тип`,
    - `Изменить URL`,
    - `Переключить перевод`,
    - `Изменить язык по умолчанию`.
- Реализованы новые edit-flow в `bot/handlers/sources.py`:
  - FSM-поток изменения `type` (`rss|site`),
  - FSM-поток изменения `url` (базовая валидация `http(s)`),
  - toggle `translate_enabled` через чтение текущего source и `PUT`,
  - FSM-поток изменения `default_target_language`.
- Сохранена существующая логика Iteration 11:
  - создание источника через FSM,
  - редактирование `name` и `schedule_cron`,
  - parse-now / enable-toggle / delete.

### Измененные файлы (ключевые)
- `bot/handlers/sources.py`
- `tests/bot/test_sources_handler_helpers.py`
- `docs/BOT_GUIDE.md`
- `docs/TESTING.md`
- `docs/ITERATIONS_LOG.md`
- `README.md`

### Тесты и проверки
- Расширен тест `tests/bot/test_sources_handler_helpers.py`:
  - проверка новых callback-кнопок source-card:
    - `source_edit_type_<id>`,
    - `source_edit_url_<id>`,
    - `source_edit_translate_<id>`,
    - `source_edit_lang_<id>`.
- Полный прогон тестов и smoke-check выполняется после pre-test commit в рамках итерации.

### Ограничения на текущем шаге
- Для `default_target_language` в боте используется базовая длиновая проверка (минимум 2 символа); строгая валидация кодов языка остается на уровне API/бизнес-логики.
- Поле `extraction_rules` по-прежнему редактируется через API (в bot UI пока не добавлено).

---

## Итерация 15 — Операционный раздел в Telegram-боте (queue/health)

### Что сделано
- Добавлен новый bot-handler `bot/handlers/ops.py` для операционного мониторинга:
  - callback `show_ops` открывает меню операционных действий (только для admin),
  - callback `ops_queue_stats` запрашивает `GET /api/queue/stats`,
  - callback `ops_readiness` запрашивает `GET /health/ready`.
- Реализовано форматирование статуса для удобного чтения в чате:
  - `_format_queue_stats(...)`:
    - Redis OK/ERROR,
    - worker alive/down + last seen,
    - сводка по очередям (`queued/started/failed/scheduled`),
  - `_format_ready(...)`:
    - readiness status,
    - `redis_ok`,
    - `worker_alive`,
    - `worker_last_seen`.
- Добавлена inline-клавиатура операционного раздела:
  - кнопки `Обновить queue stats` и `Проверить readiness`.
- Раздел интегрирован в бота:
  - новая кнопка главного меню `Операционка`,
  - подключение router `ops` в `bot/main.py`,
  - экспорт `ops` в `bot/handlers/__init__.py`.

### Измененные файлы (ключевые)
- `bot/handlers/ops.py`
- `bot/keyboards/main_menu.py`
- `bot/main.py`
- `bot/handlers/__init__.py`
- `tests/bot/test_ops_handler_helpers.py`
- `docs/BOT_GUIDE.md`
- `docs/TESTING.md`
- `docs/ITERATIONS_LOG.md`
- `README.md`

### Тесты и проверки
- Добавлен новый тестовый модуль:
  - `tests/bot/test_ops_handler_helpers.py`
  - проверяет:
    - состав ops keyboard,
    - формат текста queue stats,
    - формат readiness summary.
- Полный прогон тестов и smoke-check выполняется после pre-test commit в рамках итерации.

### Ограничения на текущем шаге
- Операционный раздел доступен только администраторам (`TELEGRAM_ADMIN_IDS`), но в MVP остается текстовым (без графиков/истории).
- В боте пока не реализованы операторские действия над failed jobs (requeue из UI); для этого используется API `/api/queue/failed/{job_id}/requeue`.

---

## Итерация 16 — Bot settings + failed requeue из UI

### Что сделано
- Закрыт "мертвый" пункт главного меню `Настройки`:
  - добавлен новый handler `bot/handlers/settings.py`,
  - реализован callback `show_settings`.
- Добавлен API для пользовательских настроек:
  - `GET /api/users/{telegram_user_id}/settings`,
  - `POST /api/users/{telegram_user_id}/settings`,
  - lazy upsert пользователя в таблицу `users` при первом обращении.
- Реализованы настройки редактора в боте:
  - `default_target_language` (FSM-ввод),
  - `enable_images` (toggle),
  - хранение в `users.settings`.
- Расширен ops-раздел для операторских действий:
  - добавлена кнопка `Показать failed jobs`,
  - добавлен endpoint `GET /api/queue/failed` (список marker jobs),
  - в боте отображаются кнопки `Requeue <job_id>` для ручного повторного запуска,
  - сохранен fallback `/requeue_failed <job_id>`.
- Обновлена главная клавиатура:
  - удален дублирующий/нецелевой пункт `Правила модерации` из main menu (админ-функция остается через `/admin`),
  - оставлены `Черновики / Источники / Операции / Настройки`.

### Измененные файлы (ключевые)
- `app/api/routers/users.py`
- `app/api/routers/queue_admin.py`
- `app/api/routers/__init__.py`
- `app/main.py`
- `bot/handlers/settings.py`
- `bot/handlers/ops.py`
- `bot/handlers/__init__.py`
- `bot/main.py`
- `bot/keyboards/main_menu.py`
- `tests/bot/test_settings_handler_helpers.py`
- `tests/bot/test_ops_handler_helpers.py`
- `docs/BOT_GUIDE.md`
- `docs/TESTING.md`
- `docs/ITERATIONS_LOG.md`
- `README.md`

### Тесты и проверки
- Добавлены/расширены bot helper tests:
  - `tests/bot/test_settings_handler_helpers.py`:
    - keyboard настроек,
    - текст отображения настроек.
  - `tests/bot/test_ops_handler_helpers.py`:
    - наличие `ops_failed_list`,
    - keyboard failed requeue действий.
- Полный прогон тестов и smoke-check выполняется после pre-test commit в рамках итерации.

### Ограничения на текущем шаге
- В settings пока нет UI для выбора пресетов/моделей по умолчанию на пользователя (доступно к расширению).
- `GET /api/queue/failed` возвращает marker job IDs без enriched metadata (время/ошибка), это operator-MVP.

---

## Итерация 17 — Production webhook mode для Telegram-бота

### Что сделано
- Реализован рабочий webhook endpoint вместо placeholder:
  - `POST /bot/webhook` теперь:
    - принимает Telegram update payload,
    - валидирует его через `aiogram.types.Update`,
    - передает update в `Dispatcher.feed_update(...)`.
- Добавлена проверка секрета webhook:
  - поддержка заголовка `X-Telegram-Bot-Api-Secret-Token`,
  - при заданном `TELEGRAM_WEBHOOK_SECRET` некорректный secret возвращает `401`.
- Унифицирован runtime для polling и webhook:
  - новый общий модуль `bot/runtime.py` с singleton `Bot`/`Dispatcher`,
  - общий helper регистрации bot commands (`ensure_bot_commands`),
  - корректное закрытие bot session (`close_bot_session`) на shutdown.
- Обновлен запуск бота в polling-режиме:
  - `bot/main.py` теперь использует общий runtime и общий set commands.
- API startup/shutdown синхронизирован с runtime бота:
  - на startup API выставляет bot commands,
  - на shutdown закрывает shared bot session.
- Добавлены новые конфигурационные параметры:
  - `TELEGRAM_WEBHOOK_SECRET`,
  - `TELEGRAM_USE_WEBHOOK` (флаг режима в окружении для эксплуатации).

### Измененные файлы (ключевые)
- `app/api/routers/bot_webhook.py`
- `app/main.py`
- `bot/runtime.py`
- `bot/main.py`
- `core/config.py`
- `.env.example`
- `tests/api/test_bot_webhook.py`
- `docs/API_REFERENCE.md`
- `docs/DEPLOY_AND_OPERATIONS.md`
- `docs/TESTING.md`
- `docs/ITERATIONS_LOG.md`
- `README.md`

### Тесты и проверки
- Добавлен новый API-тест:
  - `tests/api/test_bot_webhook.py`
  - проверяет:
    - `401` при неверном webhook secret,
    - успешную обработку update и вызов `Dispatcher.feed_update` при корректном secret.
- Полный прогон тестов и smoke-check выполняется после pre-test commit в рамках итерации.

### Ограничения на текущем шаге
- В текущем webhook flow не реализован endpoint для автоматического `setWebhook`/`deleteWebhook` управления через API (операция выполняется через Bot API/операционные команды).
- Режим `TELEGRAM_USE_WEBHOOK` добавлен как конфигурационный флаг для эксплуатации, переключение процесса polling/webhook остается на уровне deployment-профиля.

---

## Итерация 18 — Webhook operations API + mode-aware startup

### Что сделано
- Закрыт эксплуатационный зазор webhook-режима:
  - добавлены endpoints управления webhook в API:
    - `GET /bot/webhook/info`,
    - `POST /bot/webhook/set`,
    - `POST /bot/webhook/delete`.
- Реализована обвязка runtime для webhook-операций:
  - `bot/runtime.py` расширен методами:
    - `get_webhook_info()`,
    - `set_webhook(url, secret_token)`,
    - `delete_webhook(drop_pending_updates)`.
- Добавлена конфигурация для production webhook:
  - `TELEGRAM_WEBHOOK_URL` в `core/config.py` и `.env.example`.
- Сделан mode-aware запуск polling-процесса:
  - `bot/main.py` при `TELEGRAM_USE_WEBHOOK=true` не запускает polling и завершает процесс с информационным логом.
- Сохранена обратная совместимость:
  - webhook ingress `POST /bot/webhook` из Iteration 17 продолжает работать без изменений контракта.

### Измененные файлы (ключевые)
- `app/api/routers/bot_webhook.py`
- `bot/runtime.py`
- `bot/main.py`
- `core/config.py`
- `.env.example`
- `tests/api/test_bot_webhook.py`
- `docs/API_REFERENCE.md`
- `docs/DEPLOY_AND_OPERATIONS.md`
- `docs/TESTING.md`
- `docs/ITERATIONS_LOG.md`
- `README.md`

### Тесты и проверки
- Расширен `tests/api/test_bot_webhook.py`:
  - проверка `GET /bot/webhook/info`,
  - проверка `POST /bot/webhook/set` (payload и fallback на env),
  - проверка `POST /bot/webhook/delete`,
  - проверка `400`, если URL для set отсутствует.
- Полный прогон тестов и smoke-check выполняется после pre-test commit в рамках итерации.

### Ограничения на текущем шаге
- Webhook management endpoints не ограничены отдельной admin-аутентификацией на уровне API (в MVP предполагается эксплуатационный perimeter).
- `TELEGRAM_USE_WEBHOOK` управляет запуском polling-процесса, но разделение compose-профилей остается задачей deployment-конфигурации.

---

## Итерация 19 — Webhook security hardening + Ops integration

### Что сделано
- Закрыт риск незащищенного webhook-операционного API:
  - для `GET /bot/webhook/info`, `POST /bot/webhook/set`, `POST /bot/webhook/delete`
    добавлена проверка заголовка `X-Webhook-Admin-Token`,
  - токен берется из `WEBHOOK_ADMIN_TOKEN`,
  - при несовпадении возвращается `401 Invalid webhook admin token`.
- Добавлена конфигурация:
  - `WEBHOOK_ADMIN_TOKEN` в `core/config.py` и `.env.example`.
- Расширен ops-раздел Telegram-бота для работы с webhook:
  - кнопка `Webhook info` (вызов `/bot/webhook/info`),
  - кнопка `Webhook set` (вызов `/bot/webhook/set` с fallback на env),
  - кнопка `Webhook delete` (вызов `/bot/webhook/delete`),
  - в запросы автоматически добавляется `X-Webhook-Admin-Token` при заданном `WEBHOOK_ADMIN_TOKEN`.
- Сохранена совместимость ingress endpoint:
  - `POST /bot/webhook` продолжает валидировать `X-Telegram-Bot-Api-Secret-Token`
    и не требует `WEBHOOK_ADMIN_TOKEN`.

### Измененные файлы (ключевые)
- `core/config.py`
- `app/api/routers/bot_webhook.py`
- `bot/handlers/ops.py`
- `.env.example`
- `tests/api/test_bot_webhook.py`
- `tests/bot/test_ops_handler_helpers.py`
- `docs/API_REFERENCE.md`
- `docs/BOT_GUIDE.md`
- `docs/DEPLOY_AND_OPERATIONS.md`
- `docs/TESTING.md`
- `docs/ITERATIONS_LOG.md`
- `README.md`

### Тесты и проверки
- Расширен `tests/api/test_bot_webhook.py`:
  - проверка `401` для webhook management endpoint при неверном `X-Webhook-Admin-Token`,
  - существующие позитивные кейсы для info/set/delete обновлены с учетом admin token.
- Расширен `tests/bot/test_ops_handler_helpers.py`:
  - проверка новых webhook-кнопок в ops keyboard,
  - проверка helper `_webhook_headers()` (пустой/заполненный token).
- Полный прогон тестов и smoke-check выполняется после pre-test commit в рамках итерации.

### Ограничения на текущем шаге
- В MVP webhook management защищен единым shared-токеном (`WEBHOOK_ADMIN_TOKEN`) без ротации/TTL и без отдельной ролевой матрицы API.
- В ops-интерфейсе Telegram webhook set использует конфигурационный URL (`TELEGRAM_WEBHOOK_URL`); интерактивный ввод URL в боте пока не реализован.
