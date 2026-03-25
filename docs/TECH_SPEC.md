# Техническое задание (ТЗ): Система парсинга новостей с мультиязычным переводом, редактурой в Telegram-боте и публикацией в канал

## Оглавление

- [1. Цель и охват](#1-tsel-i-okhvat)
- [2. Роли и доступы](#2-roli-i-dostupy)
- [3. Функциональные требования](#3-funktsionalnye-trebovaniya)
  - [3.1. Источники и парсинг](#31-istochniki-i-parsing)
  - [3.2. Язык и перевод](#32-yazyk-i-perevod)
  - [3.3. Модерация и черные списки](#33-moderatsiya-i-chernye-spiski)
  - [3.4. Telegram-бот (редактура)](#34-telegram-bot-redaktura)
  - [3.5. LLM‑обработка (OpenRouter)](#35-llmobrabotka-openrouter)
  - [3.6. Публикация в Telegram-канал](#36-publikatsiya-v-telegram-kanal)
  - [3.7. Хранение и очистка](#37-khranenie-i-ochistka)
- [4. Нефункциональные требования](#4-nefunktsionalnye-trebovaniya)
- [5. Архитектура (высокоуровнево)](#5-arkhitektura-vysokourovnevo)
- [6. Технологический стек](#6-tekhnologicheskiy-stek)
- [7. Модель данных (схемы)](#7-model-dannykh-skhemy)
- [8. Взаимодействия и API](#8-vzaimodeystviya-i-api)
- [9. Потоки и очереди (MVP с APScheduler)](#9-potoki-i-ocheredi-mvp-s-apscheduler)
- [10. Telegram-бот: UX и команды](#10-telegram-bot-ux-i-komandy)
- [11. Правила форматирования постов](#11-pravila-formatirovaniya-postov)
- [12. Интеграция с OpenRouter (LLM/перевод)](#12-integratsiya-s-openrouter-llmperevod)
- [13. Библиотека промптов (шаблоны для Cursor/бота)](#13-biblioteka-promptov-shablony-dlya-cursorbota)
- [14. Конфигурация и переменные окружения](#14-konfiguratsiya-i-peremennye-okruzheniya)
- [15. Обработка ошибок, ретраи, идемпотентность](#15-obrabotka-oshibok-retrai-idempotentnost)
- [16. Тестирование и критерии приемки](#16-testirovanie-i-kriterii-priemki)
- [17. Деплой и эксплуатация](#17-deploy-i-ekspluatatsiya)
- [18. Пошаговый план реализации (итерации)](#18-poshagovyy-plan-realizatsii-iteratsii)
- [19. Vibe Coding в Cursor: рабочие промпты и шаги](#19-vibe-coding-v-cursor-rabochie-prompty-i-shagi)
- [20. Риски и меры](#20-riski-i-mery)
- [21. Артефакты на выходе](#21-artefakty-na-vykhode)



## 1. Цель и охват
- **Что строим**: Конвейер «сайт/RSS → парсинг → авто‑перевод → модерация/редактура в Telegram → LLM‑обработка → публикация в Telegram-канал».
- **Объемы**: до 30 источников; 2–3 статьи в день; до 3 редакторов одновременно.
- **Медиа**: изображения опционально (одно основное изображение на пост по возможности).
- **Хранение**: сырые данные, черновики и логи — 3 месяца (90 дней).
- **Интерфейсы**: MVP — только Telegram-бот (без веб‑UI). Настройка промптов и правил — через бота.
- **Языки**: сбор на разных языках, авто‑перевод в целевой язык редакции (по умолчанию RU) до попадания к редактору.


## 2. Роли и доступы
- **Админ**:
  - Управляет источниками, расписаниями, правилами модерации.
  - Настраивает промпты/пресеты и модели (через бота).
  - Управляет целевыми каналами и шаблонами постов.
- **Редактор**:
  - Просматривает переведенные черновики, запускает LLM‑пресеты, корректирует и утверждает публикации.
- **Система**:
  - Парсинг, перевод, дедупликация, публикация, логи, ретраи.


## 3. Функциональные требования

### 3.1. Источники и парсинг
- **Типы источников**: RSS и веб‑страницы.
- **Настройки на источник**: URL/шаблоны, периодичность, включен/выключен, целевой язык (по умолчанию RU), правила извлечения (CSS/XPath/Readability).
- **Парсинг по расписанию (батчами), нормализация HTML, извлечение**: заголовок, тело, дата, автор (если есть), изображения.
- **Дедупликация**:
  - **Базовая**: нормализованный URL + хеш очищенного контента.
  - На этапе MVP кросс‑языковая дедупликация не обязательна (опция фазы 2).


### 3.2. Язык и перевод
- Авто‑определение языка исходника.
- Автоматический перевод в целевой язык до попадания в ленту редактора.
- **Пресеты перевода**: «буквальный», «редакционный стиль», «сохранить имена/числа», «сохранить списки».
- Кэш переводов по хешу контента; повторное использование при дубликатах.
- Возможность повторного перевода из бота с выбором пресета/модели.
- **В карточке**: переключатель «перевод/оригинал», метка исходного языка.


### 3.3. Модерация и черные списки
- **Черный список источников (домены/паттерны URL)**: блокировать на входе.
- **Черный список слов/фраз/регэкспов**: помечать «на проверке» или блокировать (под настройку).
- **В карточке показывать, какие правила сработали; быстрые действия**: «Пропустить», «Отклонить (причина)», «Игнорировать правило для этой статьи».


### 3.4. Telegram-бот (редактура)
- Авторизация по белому списку `telegram_user_id`.
- **Лента**: новые, помеченные, одобренные; фильтры по источнику/языку/статусу; поиск по заголовку.
- **Карточка новости**:
  - **Источник, дата, язык (EN→RU), заголовок/лид/тело (перевод), кнопки**: Оригинал | Перевести заново | Резюме | Переписать в стиле | Заголовок/Хэштеги | Утвердить | Отклонить | Опубликовать.
  - Отображение изображения (если найдено).
- **Планирование публикации**: немедленная или отложенная.
- **Админ‑меню**:
  - **Источники**: список/добавить/изменить/отключить.
  - **Правила модерации**: домены/слова (добавить/удалить/включить/режим флаг/блок).
  - Промпты/пресеты LLM: просмотр/редактирование; выбор моделей.
  - Каналы и шаблоны постов.


### 3.5. LLM‑обработка (OpenRouter)
- **Типы задач**: перевод, резюме, перепись под стиль канала, генерация заголовка и хэштегов.
- **Управление пресетами**: редактируемые системные/пользовательские промпты через бота.
- **Настройки ограничений**: макс. токены, таймауты, ретраи; логирование стоимости.


### 3.6. Публикация в Telegram-канал
- Выбор канала перед публикацией.
- **Шаблоны поста**: заголовок + лид/резюме + основной текст + хэштеги + ссылка на оригинал; поддержка Markdown/HTML.
- **Ограничения Telegram**: автоматическое обрезание/разбиение длинных сообщений.
- **Вложения**: одно опциональное изображение (если доступно и валидно).


### 3.7. Хранение и очистка
- Срок жизни всех сущностей и логов — 90 дней (ежесуточная очистка).
- Экспорт выборок в CSV/JSON по запросу (опционально).


## 4. Нефункциональные требования
- **Надежность**: идемпотентность по хешу контента, ретраи сетевых операций (3 попытки с экспоненциальной задержкой).
- **Производительность**: текущие объемы малы; целевое время от парсинга до появления в боте — не более $5$ минут при нормальной нагрузке.
- **Безопасность**: хранение ключей в секретах окружения; разграничение прав (админ/редактор); аудит действий модерации и публикаций.
- **Наблюдаемость**: метрики по шагам конвейера, журнал ошибок, дашборд по стоимости LLM/перевода (стоимость на $1000$ слов).
- **Стоимость**: кэширование результатов LLM/перевода; возможность выбора экономичных моделей.


## 5. Архитектура (высокоуровнево)
- **Компоненты**:
  - Backend/API (FastAPI).
  - Планировщик задач (APScheduler).
  - Парсер (RSS + веб‑скрапинг).
  - Переводчик/LLM‑воркер (через OpenRouter).
  - Публикатор в Telegram.
  - Telegram‑бот (aiogram).
  - БД (PostgreSQL), кэш (Redis — опционально).
- **Потоки данных**:
  - Планировщик → Парсер → Нормализация/детект языка → Дедупликация → Перевод → Черновик → Бот (редактура) → LLM‑обработка → Утверждение → Публикация → Логи.


## 6. Технологический стек
- **Язык/бэкенд**: Python 3.11+, FastAPI.
- **Бот**: aiogram 3.x (webhook или long‑polling).
- **Парсинг**: `feedparser`, `readability-lxml`, `beautifulsoup4`/`lxml`, `trafilatura` (опц.).
- **Очереди/планирование**: `APScheduler` (MVP). Опц.: Redis + RQ/Celery в фазе 2.
- **БД**: PostgreSQL 14+.
- **Кэш**: Redis (опц., для кэша переводов/скоринга).
- **Логи/мониторинг**: `structlog`/`loguru`, Prometheus экспортер, Sentry (опц.).
- **Деплой**: Docker, docker‑compose на одном VPS.


## 7. Модель данных (схемы)
- **Таблицы и поля (минимум MVP)**:

```
-- PostgreSQL DDL (черновик)

CREATE TABLE sources (
  id SERIAL PRIMARY KEY,
  name TEXT NOT NULL,
  type TEXT NOT NULL CHECK (type IN ('rss','site')),
  url TEXT NOT NULL,
  enabled BOOLEAN NOT NULL DEFAULT TRUE,
  schedule_cron TEXT,                     -- "*/15 * * * *" и т.п.
  translate_enabled BOOLEAN NOT NULL DEFAULT TRUE,
  default_target_language TEXT NOT NULL DEFAULT 'ru',
  extraction_rules JSONB,                 -- CSS/XPath/Readability опции
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE articles_raw (
  id BIGSERIAL PRIMARY KEY,
  source_id INT REFERENCES sources(id),
  url TEXT NOT NULL,
  title_raw TEXT,
  content_raw TEXT,
  media JSONB,                            -- [{url, type, alt}]
  published_at TIMESTAMPTZ,
  fetched_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  language_detected TEXT,
  hash_original TEXT NOT NULL,            -- хеш очищенного исходника
  UNIQUE (url),
  UNIQUE (hash_original, source_id)
);

CREATE TABLE articles_draft (
  id BIGSERIAL PRIMARY KEY,
  article_raw_id BIGINT REFERENCES articles_raw(id) ON DELETE CASCADE,
  target_language TEXT NOT NULL DEFAULT 'ru',
  title_translated TEXT,
  content_translated TEXT,
  translation_engine TEXT,                -- openrouter:model-id
  translation_preset TEXT,
  translation_quality_score NUMERIC,      -- 0..1
  status TEXT NOT NULL DEFAULT 'new',     -- new/flagged/approved/rejected/published
  rejection_reason TEXT,
  flags JSONB,                            -- сработавшие правила модерации
  media JSONB,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE llm_tasks (
  id BIGSERIAL PRIMARY KEY,
  draft_id BIGINT REFERENCES articles_draft(id) ON DELETE CASCADE,
  task_type TEXT NOT NULL,                -- translation/summary/rewrite/title/hashtags
  preset TEXT,
  model TEXT,
  status TEXT NOT NULL DEFAULT 'queued',  -- queued/running/success/error
  prompt TEXT,
  result TEXT,
  tokens_in INT,
  tokens_out INT,
  cost_usd NUMERIC(10,4),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  error TEXT
);

CREATE TABLE publications (
  id BIGSERIAL PRIMARY KEY,
  draft_id BIGINT REFERENCES articles_draft(id) ON DELETE SET NULL,
  channel_id BIGINT,
  message_id BIGINT,
  status TEXT NOT NULL DEFAULT 'queued',  -- queued/scheduled/published/error
  scheduled_at TIMESTAMPTZ,
  published_at TIMESTAMPTZ,
  target_language TEXT NOT NULL DEFAULT 'ru',
  log TEXT
);

CREATE TABLE moderation_rules (
  id SERIAL PRIMARY KEY,
  kind TEXT NOT NULL,                     -- domain_blacklist/keyword_blacklist
  pattern TEXT NOT NULL,                  -- домен или regex
  action TEXT NOT NULL,                   -- block/flag
  enabled BOOLEAN NOT NULL DEFAULT TRUE,
  comment TEXT
);

CREATE TABLE users (
  id SERIAL PRIMARY KEY,
  telegram_user_id BIGINT UNIQUE NOT NULL,
  role TEXT NOT NULL CHECK (role IN ('admin','editor')),
  display_name TEXT,
  settings JSONB,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
```


## 8. Взаимодействия и API
- **Подход**: Telegram-бот работает через вебхук к `Backend/API`. Админ/редакторские действия — методами API. Внутренние сервисы используют фоновые задачи.

Основные эндпоинты (черновик):
- **Источники**:
  - `GET /api/sources` — список.
  - `POST /api/sources` — добавить/обновить.
  - `POST /api/sources/{id}/toggle` — включить/выключить.
- **Черновики**:
  - `GET /api/drafts?status=new|flagged|approved&q=...`
  - `GET /api/drafts/{id}`
  - `POST /api/drafts/{id}/approve`
  - `POST /api/drafts/{id}/reject` (reason)
- LLM:
  - `POST /api/llm/tasks` — создать задачу (preset, model, task_type, draft_id).
  - `GET /api/llm/tasks/{id}` — статус/результат.
- **Публикации**:
  - `POST /api/publications` — создать (draft_id, channel_id, schedule).
  - `GET /api/publications/{id}`
- **Модерация**:
  - `GET /api/moderation/rules`
  - `POST /api/moderation/rules`
  - `POST /api/moderation/rules/{id}/toggle`

Webhook бота:
- `POST /bot/webhook` — обработка апдейтов (aiogram).


## 9. Потоки и очереди (MVP с APScheduler)
- **Задачи планировщика**:
  - Парсинг по источникам.
  - Очистка данных старше 90 дней.
  - Ретраи неуспешных публикаций/LLM‑задач.
- **Воркфлоу сбора**:
  - Задача парсинга → загрузка RSS/HTML → извлечение → очистка → детект языка → хеш → проверка дублей → модерация (чёрные списки) → при необходимости пометить → перевод (OpenRouter) → сохранить `ArticleDraft`.
- **Воркфлоу редактора**:
  - Открыть ленту → карточка → опции LLM → правка/утверждение → публикация/планирование.
- **Воркфлоу публикации**:
  - Формирование текста по шаблону → проверка длины и форматирования → отправка через Telegram Bot API → запись `message_id`/статусов.


## 10. Telegram-бот: UX и команды
- **Команды/меню**:
  - `/start` — авторизация, помощь.
  - **«Лента» — фильтры**: статус/источник/язык; пагинация.
  - «Настройки» — целевой язык, изображение в постах (вкл/выкл), пресеты по умолчанию.
  - **«Админ» (только админы)**: Источники | Правила модерации | Пресеты/модели | Каналы/шаблоны.
- **Карточка черновика**:
  - **Текст перевода (заголовок/лид/тело), кнопки**:
    - «Оригинал»/«Перевод»
    - «Перевести заново» (выбор пресета/модели)
    - «Резюме»
    - «Переписать в стиле»
    - «Заголовок/Хэштеги»
    - «Утвердить»
    - «Отклонить» (причина)
    - «Опубликовать» (выбор канала; «Сейчас» или «Запланировать»)


## 11. Правила форматирования постов
- **Формат**: Markdown (предпочтительно) или HTML (настраиваемо).
- **Шаблон по умолчанию**:
  - Заголовок (жирный)
  - Короткий лид/резюме (2–3 предложения)
  - Основной текст (абзацы/списки)
  - Хэштеги (3–7, без кликбейта)
  - Ссылка на оригинал (с UTM — опционально)
- **Ограничения Telegram**:
  - Проверка длины; автоматическое разбиение на несколько сообщений, если нужно.
  - Очистка неподдерживаемой разметки, экранирование символов.
- **Изображения**:
  - Одно основное, если доступно и проходит проверку доступности.
  - Подпись к фото — часть основного текста; запасной вариант — текстовый пост без изображения.


## 12. Интеграция с OpenRouter (LLM/перевод)
- **Настройки**:
  - **Секрет**: `OPENROUTER_API_KEY`.
  - **Базовый URL**: `https://openrouter.ai/api/v1/chat/completions`.
  - **Модели (пример)**: `google/translate` или универсальная `openai/gpt-4o-mini`, для переписи: `anthropic/claude-3-haiku`/`gpt-4o-mini`, настраиваемо из бота.
- **Пример запроса**:

```python
import httpx

async def call_openrouter(model: str, system_prompt: str, user_prompt: str):
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": 0.2,
        "max_tokens": 1200,
    }
    async with httpx.AsyncClient(timeout=60) as client:
        r = await client.post("https://openrouter.ai/api/v1/chat/completions",
                              headers=headers, json=payload)
        r.raise_for_status()
        data = r.json()
        return data["choices"][0]["message"]["content"]
```


## 13. Библиотека промптов (шаблоны для Cursor/бота)
- **Переменные**: `{{source_lang}}`, `{{target_lang}}`, `{{title}}`, `{{content}}`, `{{style_guide}}`, `{{glossary}}`, `{{max_len}}`.

```markdown
# system: translation_editorial
Ты — профессиональный редактор-переводчик новостей. Стиль: нейтральный, информативный, без кликбейта. Сохраняй факты, числа, имена собственные и структуру (списки/цитаты).

# user:
Переведи с {{source_lang}} на {{target_lang}} следующий материал.
Требования:
- Сохраняй структуру и форматирование списков.
- Исправляй мелкие грамматические ошибки.
- Не добавляй мнений.
Глоссарий (если есть): {{glossary}}

Заголовок:
{{title}}

Текст:
{{content}}
```

```markdown
# system: summarization
Ты — редактор новостей. Сделай краткое резюме, выделив главное. Без оценочных суждений.

# user:
Сформируй резюме до {{max_len}} символов. Язык: {{target_lang}}.
Текст:
{{content}}
```

```markdown
# system: rewrite_style
Ты — копирайтер редакции. Перепиши текст в фирменном стиле канала: лаконично, короткие абзацы, без кликбейта.

# user:
Перепиши на {{target_lang}}. Добавь 3–5 хэштегов по теме (без редких и брендовых).
Текст:
{{content}}
```

```markdown
# system: title_hashtags
Ты — заголовочник. Заголовок информативный, до 80 символов, без клика.
Хэштеги: 3–7, общие и релевантные.

# user:
Сгенерируй заголовок и список хэштегов на {{target_lang}}.
Контент:
{{content}}
```


## 14. Конфигурация и переменные окружения
- **Обязательные**:
  - `TELEGRAM_BOT_TOKEN`
  - `TELEGRAM_ADMIN_IDS` (через запятую)
  - `TELEGRAM_CHANNEL_IDS` (map в JSON: alias→id)
  - `DATABASE_URL` (PostgreSQL)
  - `OPENROUTER_API_KEY`
- **Опциональные**:
  - `REDIS_URL`
  - `APP_BASE_URL` (для вебхука)
  - `LOG_LEVEL`
  - `DEFAULT_TARGET_LANGUAGE` (по умолчанию `ru`)
  - `LLM_DEFAULT_MODEL_TRANSLATE`, `LLM_DEFAULT_MODEL_REWRITE`, `LLM_DEFAULT_MODEL_SUMMARY`


## 15. Обработка ошибок, ретраи, идемпотентность
- **Сетевые операции**: до 3 попыток с экспоненциальной задержкой.
- **Идемпотентность**:
  - Парсинг и сохранение по `hash_original`.
  - LLM‑задачи — по `(draft_id, task_type, preset, model, prompt_hash)`.
  - Публикация — защита от дублей по `(draft_id, channel_id)`.
- **Фолбэки перевода**:
  - При недоступности OpenRouter — отложить задачу; опционально локальная MT в фазе 2.


## 16. Тестирование и критерии приемки
- **Модульные тесты**: парсеров, нормализации, дедупликации, форматирования постов.
- **Интеграционные**: полный проход «источник → публикация».
- **Приемочные критерии**:
  - Добавление до 30 источников, успешный сбор.
  - $≥ 95$% материалов корректно определяют язык.
  - Все материалы в ленте — уже переведены в RU (переключатель «оригинал/перевод» работает).
  - **Модерация**: правила срабатывают и видны в карточке; режим «флаг» по умолчанию.
  - **Утверждение и публикация в канал**: проходит, статусы и `message_id` записываются.
  - **Очистка по сроку**: данные старше 90 дней удаляются.
  - Редактирование промптов через бота — сохраняется и применяется.


## 17. Деплой и эксплуатация
- **Docker‑компоуз**: сервисы `api`, `bot`, `db` (Postgres), `scheduler` (можно в составе `api`), `redis` (опц.).
- **Вебхук бота**: установить URL `/bot/webhook` через Bot API.
- **Резервное копирование БД**: ежедневные дампы, хранение вне хоста (S3/облако).
- **Мониторинг**: экспорт базовых метрик, алерты по ошибкам публикаций и LLM‑таймаутам.


## 18. Пошаговый план реализации (итерации)
- **Итер. 1**: Скелет проекта (FastAPI + aiogram), БД, миграции; бот: авторизация, просмотр заглушек.
- **Итер. 2**: RSS‑парсер, нормализация, детект языка, базовая дедупликация; сохранение `ArticleRaw`.
- **Итер. 3**: Перевод через OpenRouter, кэш переводов; создание `ArticleDraft`; лента в боте.
- **Итер. 4**: LLM‑пресеты (резюме/перепись/заголовок), редактирование промптов в боте.
- **Итер. 5**: Публикация в Telegram‑канал, шаблоны постов, изображения (опционально).
- **Итер. 6**: Модерация и черные списки, статусы, логи, очистка 90 дней.
- **Итер. 7**: Метрики/мониторинг, полировка UX, тесты и документация.


## 19. Vibe Coding в Cursor: рабочие промпты и шаги
- **Шаг 1**: Скелет
  - **«Создай структуру проекта FastAPI + aiogram. Папки**: `app/` (api, services, models, db, workers), `bot/` (handlers, keyboards), `migrations/`, `scripts/`. Подготовь `docker-compose.yml` c Postgres. Инициализируй `pyproject.toml` с зависимостями: fastapi, uvicorn, aiogram, httpx, pydantic, sqlalchemy, alembic, feedparser, beautifulsoup4, lxml, readability-lxml.»
- **Шаг 2**: БД и миграции
  - «Сгенерируй модели SQLAlchemy по ТЗ (см. DDL) и первую миграцию Alembic.»
- **Шаг 3**: Парсер
  - «Реализуй сервис `app/services/parser.py` с функциями: `fetch_rss`, `fetch_html`, `extract_content`, `detect_language`, `compute_hash`, `upsert_article_raw`. Покрой тестами базовые случаи.»
- **Шаг 4**: Перевод
  - «Добавь `app/services/llm_client.py` и `translation_service.py` с кэшем по хешу. Подключи OpenRouter. Реализуй пресет `translation_editorial`.»
- **Шаг 5**: Черновики и бот
  - «Сделай эндпоинты `/api/drafts` и хэндлеры бота: лента, карточка, переключатель оригинал/перевод, повторный перевод.»
- **Шаг 6**: LLM‑пресеты
  - «Добавь `summary`, `rewrite_style`, `title_hashtags`, редактирование промптов в боте (хранить в БД).»
- **Шаг 7**: Публикация
  - «Реализуй `publisher_service.py`: форматирование поста, проверка длины, отправка в канал, запись статусов.»
- **Шаг 8**: Модерация
  - «Реализуй `moderation_service.py`: домены/регэкспы, маркировка/блок, отображение в карточке.»
- **Шаг 9**: Очистка и метрики
  - **«Добавь планировщик APScheduler**: парсинг по расписанию, очистка >90 дней, ретраи; базовые метрики Prometheus.»


## 20. Риски и меры
- Нестабильное качество парсинга по отдельным сайтам — ручные правила CSS/XPath на источник.
- Ошибки перевода терминов — глоссарий и повторный перевод по кнопке.
- Стоимость LLM — кэширование, выбор экономичных моделей, лимиты токенов.
- Доступность изображений — проверка; при сбоях публиковать без изображения.


## 21. Артефакты на выходе
- Репозиторий с кодом (Docker‑готов).
- Файл `README.md` с инструкциями по окружению, переменным и деплою.
- Экспорт промптов/пресетов в JSON для бэкапа.
- Набор тестов и чек‑лист приемки.

<details>
<summary>Примеры форматирования постов (Markdown)</summary>
- **Пример 1 (с фото)**:
  - **Фото**: главное изображение
  - **Подпись**:
    - **Заголовок**: «Новый релиз...» (жирный)
    - **Лид**: 1–2 предложения
    - **Основной текст**: короткие абзацы, маркеры
    - **Хэштеги**: #тема #бренд #индустрия
    - **Источник**: ссылка
- **Пример 2 (без фото)**:
  - Сообщение с тем же шаблоном в одном тексте
</summary>
</details>

<details>
<summary>Расширения после MVP (фаза 2)</summary>
- Кросс-языковая дедупликация на эмбеддингах (LaBSE/sentence‑transformers).
- **Веб‑панель**: графики, дашборды, удобное редактирование источников.
- Локальная MT (NLLB/M2M100) как фолбэк.
- Мультиканальная публикация с разными целевыми языками и стилями.
- **Расширенная аналитика**: CTR/ER по постам, A/B заголовков.
</summary>
</details>

Если нужно, могу сразу подготовить scaffold проекта (структуру папок, зависимости, базовые файлы) и стартовые промпты для Cursor, чтобы начать разработку.
