from __future__ import annotations

from sqlalchemy.orm import Session

from app.db.models.llm_preset import LLMPreset
from core.config import settings


DEFAULT_PRESETS: dict[str, dict[str, str]] = {
    "summary": {
        "task_type": "summary",
        "system_prompt": (
            "Ты — редактор новостей. Сделай краткое резюме, "
            "выделив главное. Без оценочных суждений."
        ),
        "user_prompt_template": (
            "Сформируй резюме до {{max_len}} символов. Язык: {{target_lang}}.\n\n"
            "Текст:\n{{content}}"
        ),
    },
    "rewrite_style": {
        "task_type": "rewrite",
        "system_prompt": (
            "Ты — копирайтер редакции. Перепиши текст в фирменном стиле канала: "
            "лаконично, короткие абзацы, без кликбейта."
        ),
        "user_prompt_template": (
            "Перепиши на {{target_lang}}. Добавь 3–5 хэштегов по теме.\n\n"
            "Текст:\n{{content}}"
        ),
    },
    "title_hashtags": {
        "task_type": "title_hashtags",
        "system_prompt": (
            "Ты — заголовочник. Заголовок информативный, до 80 символов, "
            "без кликбейта. Хэштеги: 3–7, релевантные."
        ),
        "user_prompt_template": (
            "Сгенерируй заголовок и список хэштегов на {{target_lang}}.\n\n"
            "Контент:\n{{content}}"
        ),
    },
}


class LLMPresetService:
    def ensure_default_presets(self, db: Session) -> None:
        default_models = {
            "summary": settings.LLM_DEFAULT_MODEL_SUMMARY,
            "rewrite_style": settings.LLM_DEFAULT_MODEL_REWRITE,
            "title_hashtags": settings.LLM_DEFAULT_MODEL_REWRITE,
        }
        for name, config in DEFAULT_PRESETS.items():
            existing = db.query(LLMPreset).filter(LLMPreset.name == name).first()
            if existing:
                continue
            db.add(
                LLMPreset(
                    name=name,
                    task_type=config["task_type"],
                    system_prompt=config["system_prompt"],
                    user_prompt_template=config["user_prompt_template"],
                    default_model=default_models[name],
                    enabled=True,
                )
            )
        db.commit()

    def list_presets(self, db: Session) -> list[LLMPreset]:
        self.ensure_default_presets(db)
        return db.query(LLMPreset).order_by(LLMPreset.name.asc()).all()

    def update_preset(
        self,
        db: Session,
        *,
        name: str,
        system_prompt: str | None = None,
        user_prompt_template: str | None = None,
        default_model: str | None = None,
        enabled: bool | None = None,
    ) -> LLMPreset:
        self.ensure_default_presets(db)
        preset = db.query(LLMPreset).filter(LLMPreset.name == name).first()
        if not preset:
            raise ValueError(f"Preset '{name}' not found")

        if system_prompt is not None:
            preset.system_prompt = system_prompt
        if user_prompt_template is not None:
            preset.user_prompt_template = user_prompt_template
        if default_model is not None:
            preset.default_model = default_model
        if enabled is not None:
            preset.enabled = enabled

        db.commit()
        db.refresh(preset)
        return preset

    def get_preset_or_raise(self, db: Session, name: str) -> LLMPreset:
        self.ensure_default_presets(db)
        preset = db.query(LLMPreset).filter(LLMPreset.name == name).first()
        if not preset:
            raise ValueError(f"Preset '{name}' not found")
        if not preset.enabled:
            raise ValueError(f"Preset '{name}' is disabled")
        return preset
