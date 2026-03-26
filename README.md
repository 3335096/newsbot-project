# NewsBot — система обработки новостей

Проект автоматизирует цикл подготовки новостей:
**источник (RSS/сайт) → парсинг → перевод → редактура в Telegram-боте → LLM-обработка → публикация**.

Текущая реализация ориентирована на MVP и разворачивается в Docker.

## Быстрый старт

1. Скопируйте пример переменных окружения:
   - `cp .env.example .env`
2. Заполните значения в `.env` (минимум: `DATABASE_URL`, `TELEGRAM_BOT_TOKEN`, `OPENROUTER_API_KEY`).
3. Запустите сервисы:
   - `docker compose up --build`

## Структура репозитория

- `app/` — FastAPI-приложение (API, сервисы, БД, планировщик).
- `bot/` — Telegram-бот (aiogram).
- `core/` — конфигурация приложения.
- `migrations/` — Alembic-миграции.
- `scripts/` — вспомогательные скрипты.
- `docker/` — Dockerfile-ы.
- `tests/` — тесты.
- `docs/` — комплект документации проекта.

## Документация

- Общий обзор: `docs/PROJECT_OVERVIEW.md`
- Журнал итераций (обновляется после каждого этапа): `docs/ITERATIONS_LOG.md`
- API: `docs/API_REFERENCE.md`
- Telegram-бот (UX/команды): `docs/BOT_GUIDE.md`
- БД и миграции: `docs/DB_AND_MIGRATIONS.md`
- Деплой и эксплуатация: `docs/DEPLOY_AND_OPERATIONS.md`
- Тестирование: `docs/TESTING.md`

## Миграции и база данных

- Применить миграции:
  - `alembic upgrade head`
- Сгенерировать SQL миграций (без применения):
  - `alembic upgrade head --sql`
- Резервный способ инициализации схемы:
  - `python scripts/init_db.py`

## Основные переменные окружения

См. `.env.example`. Ключевые параметры:

- `DATABASE_URL`
- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_ADMIN_IDS`
- `TELEGRAM_ALLOWED_USER_IDS`
- `TELEGRAM_CHANNEL_IDS`
- `OPENROUTER_API_KEY`
- `APP_BASE_URL`
- `DEFAULT_TARGET_LANGUAGE`
- `LLM_DEFAULT_MODEL_TRANSLATE`
- `LLM_DEFAULT_MODEL_REWRITE`
- `LLM_DEFAULT_MODEL_SUMMARY`
- `REDIS_URL`
- `QUEUE_LLM_NAME`
- `QUEUE_PUBLICATIONS_NAME`
- `QUEUE_DEFAULT_TIMEOUT_SECONDS`
- `QUEUE_RESULT_TTL_SECONDS`
- `QUEUE_JOB_RETRIES`

## Текущее состояние реализации

На данный момент завершены итерации 1–16:

- Итер. 1: каркас проекта, модели, миграции, базовая авторизация и базовые API.
- Итер. 2: RSS-парсинг, дедупликация, сохранение `articles_raw`.
- Итер. 3: перевод через OpenRouter, кэш переводов, автосоздание `articles_draft`, улучшенная карточка черновика.
- Итер. 4: пресеты LLM (summary/rewrite/title+hashtags), API управления пресетами, запуск LLM-задач из бота.
- Итер. 5: публикации в Telegram-каналы (немедленные и отложенные), шаблон поста, обработка лимитов Telegram.
- Итер. 6: модерация (правила block/flag), интеграция в pipeline, админ-управление правилами, cleanup старых данных.
- Итер. 7: monitoring (Prometheus `/metrics`, метрики API/сервисов/scheduler), UX-полировка интерфейса бота, hardening-тесты модерационного pipeline.
- Итер. 8: асинхронные очереди Redis/RQ для LLM и публикаций, worker-процесс, retry/status API и перевод scheduler на enqueue-модель.
- Итер. 9: управление источниками (`/api/sources` CRUD + валидация cron + `parse-now`), синхронизация scheduler-job по источникам и раздел `Источники` в Telegram-боте.
- Итер. 10: надежность очередей (DLQ marker queue + manual requeue endpoint), queue observability (`/api/queue/stats`, метрики queue events/depth), readiness check Redis/worker (`/health/ready`) и worker heartbeat.
- Итер. 11: расширение bot UX для источников — FSM-сценарии создания/редактирования/удаления источников прямо в Telegram (без обязательного перехода в API для базовых операций).
- Итер. 12: расширение админского UX для LLM-пресетов — inline FSM-редактирование `system_prompt` и `user_template` из карточки пресета (команды `/preset_system` и `/preset_user` сохранены как fallback).
- Итер. 13: расширение админского UX для LLM-пресетов — управление `default_model` из карточки пресета (inline FSM + команда `/preset_model` как fallback).
- Итер. 14: расширение bot UX для источников — редактирование через Telegram не только `name/cron`, но и `type`, `url`, `translate_enabled`, `default_target_language`.
- Итер. 15: операционный раздел в Telegram-боте для админов — просмотр queue stats (`/api/queue/stats`) и readiness (`/health/ready`) с быстрым обновлением через inline-кнопки.
- Итер. 16: закрытие bot settings и операций — реализован рабочий раздел `Настройки` (пользовательские параметры языка/изображений в БД через `/api/users/{telegram_user_id}/settings`) и UI‑requeue failed jobs в `Операции` (список marker jobs + кнопки requeue).
