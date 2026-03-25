from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Dict, List, Optional
import json

class Settings(BaseSettings):
    ENV: str = "dev"
    LOG_LEVEL: str = "INFO"
    APP_BASE_URL: str = "http://localhost:8000"

    DATABASE_URL: str

    TELEGRAM_BOT_TOKEN: str
    TELEGRAM_ADMIN_IDS: str = ""
    TELEGRAM_CHANNEL_IDS: str = "{}"

    OPENROUTER_API_KEY: str = ""
    LLM_DEFAULT_MODEL_TRANSLATE: str = "openai/gpt-4o-mini"
    LLM_DEFAULT_MODEL_SUMMARY: str = "openai/gpt-4o-mini"
    LLM_DEFAULT_MODEL_REWRITE: str = "openai/gpt-4o-mini"

    DEFAULT_TARGET_LANGUAGE: str = "ru"
    ENABLE_IMAGES: bool = True

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    @property
    def admin_ids(self) -> List[int]:
        if not self.TELEGRAM_ADMIN_IDS:
            return []
        return [int(x.strip()) for x in self.TELEGRAM_ADMIN_IDS.split(",") if x.strip()]

    @property
    def channel_ids(self) -> Dict[str, int]:
        try:
            return json.loads(self.TELEGRAM_CHANNEL_IDS)
        except Exception:
            return {}

settings = Settings()
