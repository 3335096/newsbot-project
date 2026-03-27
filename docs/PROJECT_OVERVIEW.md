# Обзор проекта NewsBot

## Назначение

Проект реализует конвейер обработки новостей:

1. Сбор из источников (RSS/сайт).
2. Нормализация и дедупликация.
3. Автоматический перевод в целевой язык редакции.
4. Модерация и редактура через Telegram-бота.
5. LLM-обработка (резюме, перепись, заголовок/хэштеги).
6. Публикация в Telegram-канал.

MVP ориентирован на работу через Telegram-бота без web UI.

## Текущий статус по итерациям

Текущая реализация соответствует итерациям **1–26** (включая очередь задач,
операционные API, webhook mode, security hardening admin auth, CI quality gates,
и cleanup техдолга по консистентности docs/settings flow).

Детали см. в `docs/ITERATIONS_LOG.md`.

## Архитектура (MVP)

- `app/` — FastAPI-приложение, API, сервисы, планировщик.
- `bot/` — Telegram-бот (aiogram).
- `core/` — конфигурация.
- `migrations/` — Alembic-миграции.
- `scripts/` — служебные скрипты инициализации.

Основные компоненты:

- **API (FastAPI)** — публичные и внутренние эндпоинты для бота/админа.
- **Scheduler (APScheduler)** — плановый парсинг источников, enqueue due-публикаций, cleanup.
- **ParserService** — сбор RSS/HTML, извлечение контента, хеширование, дедуп.
- **TranslationService** — перевод через OpenRouter + кэш переводов.
- **LLMTaskService** — постановка/выполнение задач summary/rewrite/title_hashtags через queue worker.
- **Bot (aiogram)** — интерфейс редактора/админа.
- **Redis + RQ Worker** — асинхронное выполнение LLM и publication jobs, retry/requeue.
- **PostgreSQL** — хранение сущностей и служебных данных.

## Основные сущности БД

- `sources`
- `articles_raw`
- `articles_draft`
- `llm_tasks`
- `llm_presets`
- `publications`
- `moderation_rules`
- `users`

Схема и миграции описаны в `docs/DB_AND_MIGRATIONS.md`.

## Ключевые функции, доступные на текущем этапе

- Парсинг RSS и извлечение контента статьи.
- Дедупликация по URL и `(source_id, hash_original)`.
- Автоперевод новых материалов в целевой язык источника.
- Создание и отображение черновиков в боте.
- Переключение карточки черновика между оригиналом и переводом.
- LLM-задачи из карточки: Summary / Rewrite style / Title+Hashtags (асинхронно через очередь).
- Публикации в каналы Telegram (queued/scheduled) с worker-обработкой и retry.
- Управление источниками, moderation rules, presets и webhook ops через API и bot admin/ops.
- Мониторинг и эксплуатация:
  - `/metrics`, `/health`, `/health/ready`,
  - `/api/queue/stats`, `/api/queue/failed`, manual requeue.

## Ограничения текущего этапа

- Основной production-диалект БД — PostgreSQL; SQLite используется как тестовый/smoke-контур.
- `users` settings API использует query-параметр `actor_user_id` для проверки прав
  (бот передает его автоматически).
- Часть проектной документации поддерживается инкрементально, source-of-truth по
  поведению — код и актуальные тесты.
