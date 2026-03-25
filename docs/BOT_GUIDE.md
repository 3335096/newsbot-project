# Руководство по Telegram-боту

Документ описывает текущие сценарии работы бота (MVP после итерации 4).

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
   - `Show original` / `Show translation`
5. Выполнять действия:
   - `Summary`
   - `Rewrite style`
   - `Title/Hashtags`
   - `Approve`
   - `Reject` (с вводом причины)

## 3. Карточка черновика

Карточка показывает:
- ID черновика
- статус
- языковую пару (`source_language -> target_language`)
- заголовок и текст (оригинал или перевод)

Инлайн-кнопки:
- `Show original` / `Show translation`
- `Summary`
- `Rewrite style`
- `Title/Hashtags`
- `Approve`
- `Reject`

## 4. LLM-действия на карточке

Кнопки запускают вызов API:
- `POST /api/llm/tasks`

Параметры:
- `draft_id`
- `task_type` (`summary` / `rewrite` / `title_hashtags`)
- `preset` (`summary` / `rewrite_style` / `title_hashtags`)

По завершении бот отправляет короткий результат (или ошибку).

## 5. Админ-функции (пресеты)

Команда:
- `/admin`

В админ-панели:
- `LLM Presets` — просмотр пресетов
- `Toggle enabled` — включение/отключение
- `Edit system prompt` — подсказка по команде
- `Edit user template` — подсказка по команде

Команды редактирования:
- `/preset_system <preset_name> <new system prompt>`
- `/preset_user <preset_name> <new user template>`

## 6. Известные ограничения текущей версии

- Редактирование пресетов через inline-формы FSM пока не реализовано — используется формат команд.
- Публикация в канал (полный workflow) будет развиваться в следующих итерациях.
- В боте пока нет полного отдельного раздела управления источниками/модерацией (кроме базовой структуры меню).
