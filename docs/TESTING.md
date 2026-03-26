# Тестирование

## Что уже покрыто

На текущий момент в репозитории есть модульные тесты:

- `tests/services/test_parser_service.py`
- `tests/services/test_publisher_service.py`
- `tests/services/test_moderation_service.py`
- `tests/services/test_parser_moderation_pipeline.py`
- `tests/services/test_queue_dispatcher.py`
- `tests/services/test_queue_dispatcher_requeue.py`
- `tests/services/test_queue_reliability.py`
- `tests/services/test_sources_router.py`
- `tests/bot/test_sources_handler_helpers.py`
- `tests/bot/test_admin_handler_helpers.py`
- `tests/bot/test_ops_handler_helpers.py`
- `tests/bot/test_settings_handler_helpers.py`

Покрытые сценарии:

1. Стабильность хэширования после нормализации текста.
2. Эвристическое определение языка (`ru`, `en`, `unknown`).
3. Извлечение контента по CSS-правилам.
4. Дедупликация `articles_raw` по URL и `(source_id, hash_original)`.
5. Проверка поведения кэша переводов на уровне пайплайна.
6. Проверка форматирования/разбиения публикаций.
7. Проверка правил модерации (`domain_blacklist`, `keyword_blacklist`) и toggle.
8. Hardening-сценарии модерации parser-пайплайна:
   - `block` блокирует создание draft,
   - `flag` помечает draft статусом `flagged`.
9. Queue dispatcher:
   - постановка `queued` и `scheduled(due)` публикаций в очередь,
   - пропуск публикаций с future `scheduled_at`,
   - проставление `queue_job_id`.
10. Sources API:
   - валидация cron при создании/обновлении источника,
   - ручной trigger `parse-now`,
   - отказ `409` для disabled источника,
   - вызов синхронизации scheduler job при create/update.
11. Queue reliability:
   - requeue логика только для failed-like статусов (`failed/stopped/canceled`),
   - worker heartbeat в Redis и проверка `worker_alive`,
   - queue-admin stats (`redis_ok`, snapshots по очередям).
12. Bot sources UX/helpers:
   - формат карточки источника и значения по умолчанию,
   - состав action-кнопок для источника (name/cron/type/url/translate/lang + parse/toggle/delete),
   - наличие кнопки создания источника в общем меню источников.
13. Bot admin UX/helpers:
   - структура админ-меню,
   - callback паттерны действий для preset-карточки
     (system/user/default_model/toggle).
14. Bot ops UX/helpers:
   - keyboard операционного раздела,
   - форматирование queue stats/readiness payload в человекочитаемый текст,
   - keyboard requeue failed jobs.
15. Bot settings UX/helpers:
   - keyboard раздела настроек,
   - отображение значений `default_target_language` и `enable_images`.
16. Webhook endpoint:
   - проверка `X-Telegram-Bot-Api-Secret-Token`,
   - прием валидного update и передача в `Dispatcher.feed_update`.
17. Webhook autosync runtime:
   - `sync_webhook_mode` корректно отрабатывает сценарии:
     - autosync disabled,
     - webhook set при `TELEGRAM_USE_WEBHOOK=true`,
     - webhook delete при polling mode,
     - skip при пустом `TELEGRAM_WEBHOOK_URL`,
     - idempotent skip если webhook уже установлен с тем же URL (`already_set`),
     - idempotent skip если webhook уже отсутствует (`already_deleted`).
18. Webhook/Admin operations API auth:
   - доступ к admin endpoint-ам API защищен заголовком `X-Admin-Api-Token`
     (если задан `ADMIN_API_TOKEN`),
   - `401` при некорректном admin token.
19. Bot ops webhook helpers:
   - наличие webhook-кнопок в `_ops_keyboard`,
   - корректная сборка admin-token заголовков в `_admin_api_headers`.
20. Admin dependency hardening:
   - rate-limit неверных попыток admin token (`429`),
   - корректная работа helper при валидном/невалидном `ADMIN_API_TOKEN`.
21. Distributed admin rate-limit:
   - Redis-backed shared limiter path (одинаковое поведение в multi-replica),
   - in-memory fallback path при недоступном Redis.

## Быстрый запуск тестов

```bash
python3 -m pytest \
  tests/services/test_parser_service.py \
  tests/services/test_publisher_service.py \
  tests/services/test_moderation_service.py \
  tests/services/test_parser_moderation_pipeline.py \
  tests/services/test_queue_dispatcher.py \
  tests/services/test_queue_dispatcher_requeue.py \
  tests/services/test_queue_reliability.py \
  tests/services/test_sources_router.py \
  tests/api/test_admin_api_token_deps.py \
  tests/api/test_bot_webhook.py \
  tests/bot/test_runtime_webhook_sync.py \
  tests/bot/test_sources_handler_helpers.py \
  tests/bot/test_admin_handler_helpers.py \
  tests/bot/test_ops_handler_helpers.py \
  tests/bot/test_settings_handler_helpers.py -q
```

## Smoke-check (рекомендуется после изменений инфраструктуры)

```bash
DATABASE_URL="sqlite:///./smoke.db" TELEGRAM_BOT_TOKEN="smoke-token" python3 -c "import app.main; print('import app.main: OK')"
DATABASE_URL="sqlite:///./smoke.db" TELEGRAM_BOT_TOKEN="smoke-token" python3 -c "import bot.main; print('import bot.main: OK')"
DATABASE_URL="sqlite:///./smoke.db" TELEGRAM_BOT_TOKEN="smoke-token" python3 -m alembic upgrade head --sql
```

## Что добавить дальше (рекомендуется)

1. Тесты для `LLMTaskService`:
   - summary/rewrite/title_hashtags с моком LLM.
2. Интеграционный тест потока:
   - `source -> articles_raw -> articles_draft -> llm_task`.
3. Негативные сценарии API:
   - невалидные preset/task_type,
   - недоступные draft/preset.
