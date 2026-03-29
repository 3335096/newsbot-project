# Railway deployment guide (step by step)

Этот гайд описывает полный запуск проекта в Railway для production.

## 1) Выберите режим запуска Telegram-бота

### Рекомендуемый режим: webhook
- Railway сервисы: `api` (web), `worker` (background), `postgres`, `redis`.
- Отдельный сервис `bot` **не нужен**.
- В этом режиме Telegram отправляет апдейты в `POST /bot/webhook` вашего API.

### Альтернативный режим: polling
- Railway сервисы: `api`, `worker`, `bot`, `postgres`, `redis`.
- Используйте только если webhook не подходит.

---

## 2) Подготовьте секреты и значения заранее

Обязательно подготовьте:
- `TELEGRAM_BOT_TOKEN`
- `ADMIN_API_TOKEN` (случайная строка минимум 32 символа)
- `TELEGRAM_WEBHOOK_SECRET` (случайная строка минимум 32 символа, для webhook режима)
- Telegram user id администраторов (`TELEGRAM_ADMIN_IDS`)

Рекомендации:
- Для `ADMIN_API_TOKEN` и `TELEGRAM_WEBHOOK_SECRET` используйте длинные случайные строки.
- Не оставляйте пустыми `TELEGRAM_ADMIN_IDS` и `TELEGRAM_ALLOWED_USER_IDS`, иначе доступ к боту может быть закрыт для всех.

---

## 3) Создайте Railway проект и сервисы

1. Создайте новый проект в Railway.
2. Подключите GitHub-репозиторий.
3. Добавьте плагины:
   - PostgreSQL
   - Redis
4. Создайте сервисы из репозитория:
   - `api` (web service)
   - `worker` (background service)
   - `bot` (только если polling режим)

> В репозитории уже есть `railway.toml` + `nixpacks.toml`.  
> Start command берется из репозитория: `bash scripts/railway_start.sh`.

---

## 4) Настройте переменные окружения

Ниже минимальный production baseline.

## 4.1 Общие переменные (для API и Worker)

| Переменная | Обязательно | Пример/значение |
|---|---:|---|
| `ENV` | да | `prod` |
| `DATABASE_URL` | да | из Railway PostgreSQL (подставьте реальное значение) |
| `REDIS_URL` | да | из Railway Redis |
| `TELEGRAM_BOT_TOKEN` | да | токен из BotFather |
| `TELEGRAM_ADMIN_IDS` | да | `123456789,987654321` |
| `TELEGRAM_ALLOWED_USER_IDS` | желательно | `123456789,987654321` |
| `ADMIN_API_TOKEN` | да | длинный случайный токен |
| `LOG_LEVEL` | желательно | `INFO` |
| `OPENROUTER_API_KEY` | если используете LLM | ключ OpenRouter |

## 4.2 Дополнительно для API (webhook режим)

| Переменная | Обязательно | Пример/значение |
|---|---:|---|
| `APP_ROLE` | да | `api` |
| `TELEGRAM_USE_WEBHOOK` | да | `true` |
| `APP_BASE_URL` | да | `https://<api-domain>.up.railway.app` |
| `TELEGRAM_WEBHOOK_URL` | да | `https://<api-domain>.up.railway.app/bot/webhook` |
| `TELEGRAM_WEBHOOK_SECRET` | да | длинный случайный токен |
| `TELEGRAM_WEBHOOK_AUTOSYNC_ON_STARTUP` | желательно | `true` |
| `TELEGRAM_WEBHOOK_DROP_PENDING_ON_SET` | опционально | `false` |
| `TELEGRAM_WEBHOOK_DROP_PENDING_ON_DISABLE` | опционально | `false` |

## 4.3 Дополнительно для Worker

| Переменная | Обязательно | Пример/значение |
|---|---:|---|
| `APP_ROLE` | да | `worker` |
| `QUEUE_LLM_NAME` | опционально | `llm` |
| `QUEUE_PUBLICATIONS_NAME` | опционально | `publications` |
| `QUEUE_FAILED_NAME` | опционально | `failed` |
| `QUEUE_JOB_RETRIES` | опционально | `3` |
| `WORKER_HEARTBEAT_TTL_SECONDS` | опционально | `60` |

## 4.4 Дополнительно для Bot (только polling)

| Переменная | Обязательно | Пример/значение |
|---|---:|---|
| `APP_ROLE` | да | `bot` |
| `TELEGRAM_USE_WEBHOOK` | да | `false` |
| `APP_BASE_URL` | да | URL API сервиса (`https://...`) |

---

## 5) Первый деплой: правильный порядок

1. Задайте переменные для `api` и `worker`.
2. Запустите первый деплой.
3. Дождитесь, пока `api` получит публичный домен Railway.
4. Убедитесь, что:
   - `APP_BASE_URL` совпадает с публичным URL API,
   - `TELEGRAM_WEBHOOK_URL` = `<APP_BASE_URL>/bot/webhook`.
5. Перезапустите `api` сервис, чтобы webhook autosync применился.

---

## 6) Проверка после деплоя (smoke checklist)

Проверяйте по порядку:

1. `GET /health` возвращает `200`.
2. `GET /health/ready` возвращает JSON со статусом Redis/worker.
3. В логах `api` есть успешный старт uvicorn и миграций.
4. В логах `worker` нет бесконечных ошибок подключения к Redis/Postgres.
5. В webhook режиме:
   - вызов `GET /bot/webhook/info` с заголовком `X-Admin-Api-Token` показывает ваш URL.

Пример:

```bash
curl -H "X-Admin-Api-Token: <ADMIN_API_TOKEN>" \
  "https://<api-domain>.up.railway.app/bot/webhook/info"
```

---

## 7) Как выкатывать обновления безопасно

1. Перед merge проверьте CI.
2. После деплоя проверьте:
   - `/health`
   - `/health/ready`
   - webhook info (если webhook режим)
3. Если менялись миграции, проверьте логи `api` на шаге `alembic upgrade head`.

---

## 8) Частые ошибки и быстрые исправления

### Ошибка: worker деплой падает с `service unavailable` / `Healthcheck failed!`
- Причина: для worker-сервиса Railway пытается делать HTTP healthcheck, но worker не поднимает web endpoint.
- Исправление:
  1. Для worker в Railway UI отключите HTTP healthcheck (или оставьте healthcheck только для `api`).
  2. В репозитории `railway.toml` убран глобальный `healthcheckPath`, чтобы не ломать background service.

### Ошибка: SQLAlchemy падает на старте с `AssertionError ... SQLCoreOperations`
- Причина: деплой собрался на Python 3.13.
- Исправление: использовать Python 3.12 для Railway (в репозитории это зафиксировано в `nixpacks.toml` и `.python-version`).
- Действия в Railway:
  1. Redeploy сервис `api` на свежем коммите.
  2. В Deploy Logs проверьте, что setup использует Python 3.12.

### Ошибка: `Invalid DSN` или проблемы с `postgres://`
- Причина: провайдер дал `postgres://`.
- В проекте есть нормализация в конфиге, но убедитесь, что `DATABASE_URL` действительно заполнен и валиден.

### Ошибка: бот не отвечает в Telegram (webhook режим)
- Проверьте `TELEGRAM_USE_WEBHOOK=true`.
- Проверьте `TELEGRAM_WEBHOOK_URL` и `APP_BASE_URL`.
- Проверьте секрет `TELEGRAM_WEBHOOK_SECRET`.
- Проверьте `GET /bot/webhook/info`.

### Ошибка: worker жив, но задачи не выполняются
- Проверьте одинаковые `REDIS_URL`, `QUEUE_*` в API и Worker.
- Проверьте `OPENROUTER_API_KEY`, если зависают LLM-задачи.

### Ошибка: никто не может пользоваться ботом
- Заполните `TELEGRAM_ADMIN_IDS`.
- При необходимости заполните `TELEGRAM_ALLOWED_USER_IDS`.

### Ошибка: `401 Invalid admin api token`
- Используйте заголовок `X-Admin-Api-Token`.
- Убедитесь, что значение совпадает с `ADMIN_API_TOKEN`.

