# Руководство по Telegram-боту

Документ описывает текущие сценарии работы бота (MVP после итерации 9).

## 1. Авторизация и доступ

- Доступ в бот ограничен whitelist:
  - `TELEGRAM_ALLOWED_USER_IDS`
  - если пусто, используется `TELEGRAM_ADMIN_IDS`
- Админ-команды доступны только пользователям из `TELEGRAM_ADMIN_IDS`.

## 2. Основной сценарий редактора

1. Нажать `/start`
2. Открыть меню и выбрать `Drafts`
3. Просматривать карточки черновиков
4. Переключать режим просмотра:
   - `Показать оригинал` / `Показать перевод`
5. Выполнять действия:
   - `Кратко (Summary)`
   - `Рерайт стиля`
   - `Заголовок/Хэштеги`
   - `Одобрить`
   - `Отклонить` (с вводом причины)
   - `Опубликовать: <channel>`

## 3. Карточка черновика

Карточка показывает:
- ID черновика
- статус
- языковую пару (`source_language -> target_language`)
- заголовок и текст (оригинал или перевод)

Инлайн-кнопки:
- `Показать оригинал` / `Показать перевод`
- `Кратко (Summary)`
- `Рерайт стиля`
- `Заголовок/Хэштеги`
- `Одобрить`
- `Отклонить`
- `Опубликовать: <channel>`

Если на черновике сработали правила модерации, в карточке показывается блок
`Флаги модерации` с краткой информацией о правилах.

## 4. LLM-действия на карточке

Кнопки запускают вызов API:
- `POST /api/llm/tasks`

Параметры:
- `draft_id`
- `task_type` (`summary` / `rewrite` / `title_hashtags`)
- `preset` (`summary` / `rewrite_style` / `title_hashtags`)

Начиная с итерации 8 задача ставится в фон:
- бот показывает `id` задачи и статус `queued`,
- результат/ошибка доступны через API:
  - `GET /api/llm/tasks/{id}`
  - `POST /api/llm/tasks/{id}/retry`

## 5. Админ-функции (пресеты и модерация)

Команда:
- `/admin`

В админ-панели:
- `LLM-пресеты` — просмотр пресетов
- `Вкл/выкл` — включение/отключение пресета
- `Изменить system prompt` — inline/FSM-редактирование
- `Изменить user template` — inline/FSM-редактирование
- `Изменить default model` — inline/FSM-редактирование
- `Правила модерации` — просмотр и переключение правил

Команды редактирования (fallback):
- `/preset_system <preset_name> <new system prompt>`
- `/preset_user <preset_name> <new user template>`
- `/preset_model <preset_name> <default_model|->`

### Inline/FSM редактирование пресетов (Iteration 12)

В карточке пресета кнопки:
- `Изменить system prompt`
- `Изменить user template`

теперь запускают stateful flow в самом боте:
1. нажать кнопку в карточке пресета,
2. ввести новый текст,
3. бот отправляет `POST /api/llm/presets/{preset_name}`,
4. возвращает подтверждение и action-кнопки пресета.

Таким образом, базовое редактирование пресетов доступно без ручного набора slash-команд.

### Inline/FSM редактирование default model (Iteration 13)

Добавлена отдельная кнопка:
- `Изменить default model`

Flow:
1. нажать кнопку в карточке пресета,
2. ввести значение модели (например, `openai/gpt-4o-mini`) или `-` для сброса,
3. бот отправляет `POST /api/llm/presets/{preset_name}` с `default_model`,
4. возвращает подтверждение и action-кнопки пресета.

## 6. Публикация из карточки

Кнопка `Опубликовать: <channel>` вызывает:
- `POST /api/publications`

Публикация выполняется асинхронно через очередь:
- API создает запись публикации и ставит задачу в Redis/RQ,
- бот показывает `id` и текущий статус (`queued`/`scheduled`).

Проверка статуса и повторная постановка:
- `GET /api/publications/{id}`
- `POST /api/publications/{id}/retry`

## 7. Раздел "Источники" (Iteration 14)

В главном меню доступна кнопка `Источники`.

Поддерживаемые действия:
- просмотр списка источников (`GET /api/sources`),
- создание источника через FSM-диалог в боте (`POST /api/sources`),
- редактирование названия (`PUT /api/sources/{id}`),
- редактирование cron (`PUT /api/sources/{id}`),
- редактирование типа (`rss|site`) (`PUT /api/sources/{id}`),
- редактирование URL (`PUT /api/sources/{id}`),
- переключение `translate_enabled` (`PUT /api/sources/{id}`),
- редактирование `default_target_language` (`PUT /api/sources/{id}`),
- ручной запуск парсинга (`POST /api/sources/{id}/parse-now`),
- включение/выключение источника (`PUT /api/sources/{id}` с полем `enabled`),
- удаление источника (`DELETE /api/sources/{id}`).

Для каждого источника показываются:
- идентификатор,
- название/тип/URL,
- признак включения,
- cron-расписание,
- настройки перевода.

## 8. Известные ограничения текущей версии

- Для источников через бот пока не реализовано редактирование `extraction_rules`; это остается на уровне API.

## 9. Операционный раздел (Iteration 15)

В главном меню добавлена кнопка `Операции` (только для администраторов).

Поддерживаемые действия:
- `Обновить queue stats`:
  - вызывает `GET /api/queue/stats`,
  - показывает состояние Redis/worker и сводку по очередям (`llm`, `publications`, `failed`).
- `Проверить readiness`:
  - вызывает `GET /health/ready`,
  - показывает `status`, `redis_ok`, `worker_alive`, `worker_last_seen`.

Для не-админов раздел недоступен (проверка по `TELEGRAM_ADMIN_IDS`).

## 10. Настройки пользователя (Iteration 16)

В меню доступна кнопка `Настройки`.

Поддерживаемые действия:
- просмотр текущих пользовательских параметров,
- изменение `default_target_language`,
- переключение `enable_images`.

Хранение:
- настройки сохраняются в профиле пользователя (`users.settings`) через API:
  - `GET /api/users/{telegram_user_id}/settings?actor_user_id=<telegram_user_id>`
  - `POST /api/users/{telegram_user_id}/settings?actor_user_id=<telegram_user_id>`

## 11. Операторские действия по failed jobs (Iteration 16)

В разделе `Операции` добавлено:
- `Показать failed jobs` — список marker jobs из failed queue,
- кнопки `Requeue <job_id>` для постановки задачи на повторную обработку.

Используемые API:
- `GET /api/queue/failed`
- `POST /api/queue/failed/{job_id}/requeue`

## 12. Webhook operations из раздела "Операции" (Iteration 19)

В разделе `Операции` для администраторов добавлены кнопки:
- `Webhook info`
- `Webhook set`
- `Webhook delete`

Действия:
- `Webhook info`:
  - вызывает `GET /bot/webhook/info`,
  - показывает текущий `url`, `pending_update_count` и `last_error`.
- `Webhook set`:
  - вызывает `POST /bot/webhook/set` (использует `TELEGRAM_WEBHOOK_URL`/`TELEGRAM_WEBHOOK_SECRET`),
  - возвращает `applied` и URL.
- `Webhook delete`:
  - вызывает `POST /bot/webhook/delete`,
  - возвращает результат `applied`.

Безопасность:
- bot отправляет unified admin header:
  - `X-Admin-Api-Token: <token>`;
- токен берется строго из `ADMIN_API_TOKEN`;
- при неверном токене API возвращает `401`.
