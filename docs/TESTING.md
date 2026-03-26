# Тестирование

## Что уже покрыто

На текущий момент в репозитории есть модульные тесты:

- `tests/services/test_parser_service.py`
- `tests/services/test_publisher_service.py`
- `tests/services/test_moderation_service.py`
- `tests/services/test_parser_moderation_pipeline.py`
- `tests/services/test_queue_dispatcher.py`
- `tests/services/test_sources_router.py`

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

## Быстрый запуск тестов

```bash
python3 -m pytest \
  tests/services/test_parser_service.py \
  tests/services/test_publisher_service.py \
  tests/services/test_moderation_service.py \
  tests/services/test_parser_moderation_pipeline.py \
  tests/services/test_queue_dispatcher.py \
  tests/services/test_sources_router.py -q
```

## Smoke-check (рекомендуется после изменений инфраструктуры)

```bash
DATABASE_URL="sqlite:///./smoke.db" TELEGRAM_BOT_TOKEN="smoke-token" python3 -c "import app.main; print('import app.main: OK')"
DATABASE_URL="sqlite:///./smoke.db" TELEGRAM_BOT_TOKEN="smoke-token" python3 -c "import bot.main; print('import bot.main: OK')"
DATABASE_URL="sqlite:///./smoke.db" TELEGRAM_BOT_TOKEN="smoke-token" python3 -m alembic upgrade head --sql
```

## Что добавить дальше (рекомендуется)

1. Тесты для `LLMPresetService`:
   - bootstrap дефолтных пресетов,
   - update/disable пресета.
2. Тесты для `LLMTaskService`:
   - summary/rewrite/title_hashtags с моком LLM.
3. Интеграционный тест потока:
   - `source -> articles_raw -> articles_draft -> llm_task`.
4. Негативные сценарии API:
   - невалидные preset/task_type,
   - недоступные draft/preset.
