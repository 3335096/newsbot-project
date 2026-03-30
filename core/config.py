import json
from typing import Dict, List, Set

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    ENV: str = "dev"
    LOG_LEVEL: str = "INFO"
    APP_BASE_URL: str = "http://localhost:8000"
    WEB_APP_URL: str = ""

    DATABASE_URL: str

    TELEGRAM_BOT_TOKEN: str
    TELEGRAM_ADMIN_IDS: str = ""
    TELEGRAM_ALLOWED_USER_IDS: str = ""
    TELEGRAM_CHANNEL_IDS: str = "{}"
    TELEGRAM_WEBHOOK_SECRET: str = ""
    TELEGRAM_USE_WEBHOOK: bool = False
    TELEGRAM_WEBHOOK_URL: str = ""
    TELEGRAM_WEBHOOK_AUTOSYNC_ON_STARTUP: bool = True
    TELEGRAM_WEBHOOK_DROP_PENDING_ON_SET: bool = False
    TELEGRAM_WEBHOOK_DROP_PENDING_ON_DISABLE: bool = False
    ADMIN_API_TOKEN: str = ""
    ADMIN_API_RATE_LIMIT_COUNT: int = 60
    ADMIN_API_RATE_LIMIT_WINDOW_SECONDS: int = 60
    ADMIN_API_AUDIT_LOG_ENABLED: bool = True
    ADMIN_API_RATE_LIMIT_REDIS_PREFIX: str = "newsbot:admin_auth:failures"
    ADMIN_API_RATE_LIMIT_ALLOW_INMEMORY_FALLBACK: bool = True

    OPENROUTER_API_KEY: str = ""
    LLM_DEFAULT_MODEL_TRANSLATE: str = "openai/gpt-4o-mini"
    LLM_DEFAULT_MODEL_SUMMARY: str = "openai/gpt-4o-mini"
    LLM_DEFAULT_MODEL_REWRITE: str = "openai/gpt-4o-mini"

    REDIS_URL: str = "redis://redis:6379/0"
    QUEUE_LLM_NAME: str = "llm"
    QUEUE_PUBLICATIONS_NAME: str = "publications"
    QUEUE_FAILED_NAME: str = "failed"
    QUEUE_DEFAULT_TIMEOUT_SECONDS: int = 600
    QUEUE_RESULT_TTL_SECONDS: int = 86400
    QUEUE_JOB_RETRIES: int = 3
    WORKER_HEARTBEAT_TTL_SECONDS: int = 60

    DEFAULT_TARGET_LANGUAGE: str = "ru"
    ENABLE_IMAGES: bool = True

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    @field_validator("DATABASE_URL", mode="before")
    @classmethod
    def _normalize_database_url(cls, value: str) -> str:
        if not isinstance(value, str):
            return value
        normalized = value.strip()
        if normalized.startswith("postgres://"):
            # Railway/Postgres providers may expose postgres:// URLs.
            # SQLAlchemy expects postgresql:// scheme.
            return "postgresql://" + normalized[len("postgres://") :]
        return normalized

    @field_validator("APP_BASE_URL", mode="before")
    @classmethod
    def _normalize_app_base_url(cls, value: str) -> str:
        if not isinstance(value, str):
            return value
        normalized = value.strip().rstrip("/")
        if not normalized:
            return normalized
        if normalized.startswith("http://") or normalized.startswith("https://"):
            return normalized
        # Railway users often paste hostnames without a scheme.
        return f"https://{normalized}"

    @field_validator("WEB_APP_URL", mode="before")
    @classmethod
    def _normalize_web_app_url(cls, value: str) -> str:
        if not isinstance(value, str):
            return value
        normalized = value.strip().rstrip("/")
        if not normalized:
            return normalized
        if normalized.startswith("http://") or normalized.startswith("https://"):
            return normalized
        return f"https://{normalized}"

    @field_validator("REDIS_URL", mode="before")
    @classmethod
    def _normalize_redis_url(cls, value: str) -> str:
        if not isinstance(value, str):
            return value
        return value.strip()

    @property
    def admin_ids(self) -> List[int]:
        if not self.TELEGRAM_ADMIN_IDS:
            return []
        return [int(x.strip()) for x in self.TELEGRAM_ADMIN_IDS.split(",") if x.strip()]

    @property
    def allowed_user_ids(self) -> Set[int]:
        allowed = {
            int(x.strip()) for x in self.TELEGRAM_ALLOWED_USER_IDS.split(",") if x.strip()
        }
        if not allowed:
            allowed = set(self.admin_ids)
        return allowed

    @property
    def channel_ids(self) -> Dict[str, int]:
        try:
            return json.loads(self.TELEGRAM_CHANNEL_IDS)
        except Exception:
            return {}

settings = Settings()
