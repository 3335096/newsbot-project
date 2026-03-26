import json
from typing import Dict, List, Set

from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    ENV: str = "dev"
    LOG_LEVEL: str = "INFO"
    APP_BASE_URL: str = "http://localhost:8000"

    DATABASE_URL: str

    TELEGRAM_BOT_TOKEN: str
    TELEGRAM_ADMIN_IDS: str = ""
    TELEGRAM_ALLOWED_USER_IDS: str = ""
    TELEGRAM_CHANNEL_IDS: str = "{}"
    TELEGRAM_WEBHOOK_SECRET: str = ""
    TELEGRAM_USE_WEBHOOK: bool = False
    TELEGRAM_WEBHOOK_URL: str = ""

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
