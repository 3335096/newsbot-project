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

## Текущее состояние реализации

На данный момент завершены итерации 1–4:

- Итер. 1: каркас проекта, модели, миграции, базовая авторизация и базовые API.
- Итер. 2: RSS-парсинг, дедупликация, сохранение `articles_raw`.
- Итер. 3: перевод через OpenRouter, кэш переводов, автосоздание `articles_draft`, улучшенная карточка черновика.
- Итер. 4: пресеты LLM (summary/rewrite/title+hashtags), API управления пресетами, запуск LLM-задач из бота.
