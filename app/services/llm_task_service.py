from __future__ import annotations

from dataclasses import dataclass
import re

from sqlalchemy.orm import Session

from app.db.models.article_draft import ArticleDraft
from app.db.models.llm_task import LLMTask
from app.services.llm_client import LLMClient
from app.services.llm_preset_service import LLMPresetService
from core.config import settings


@dataclass
class LLMTaskResult:
    task: LLMTask
    applied_to_draft: bool


class LLMTaskService:
    def __init__(self):
        self.llm_client = LLMClient()
        self.preset_service = LLMPresetService()

    async def run_task(
        self,
        db: Session,
        *,
        draft_id: int,
        task_type: str,
        preset_name: str,
        model: str | None = None,
        max_len: int = 700,
    ) -> LLMTaskResult:
        draft = db.query(ArticleDraft).filter(ArticleDraft.id == draft_id).first()
        if not draft:
            raise ValueError("Draft not found")

        preset = self.preset_service.get_preset_or_raise(db, preset_name)
        if preset.task_type != task_type:
            raise ValueError("Preset task_type does not match requested task_type")

        content = draft.content_translated or ""
        user_prompt = (
            preset.user_prompt_template
            .replace("{{target_lang}}", draft.target_language)
            .replace("{{content}}", content)
            .replace("{{max_len}}", str(max_len))
        )
        default_by_task = {
            "summary": settings.LLM_DEFAULT_MODEL_SUMMARY,
            "rewrite": settings.LLM_DEFAULT_MODEL_REWRITE,
            "title_hashtags": settings.LLM_DEFAULT_MODEL_REWRITE,
        }
        selected_model = model or preset.default_model or default_by_task.get(
            task_type, settings.LLM_DEFAULT_MODEL_REWRITE
        )

        llm_task = LLMTask(
            draft_id=draft.id,
            task_type=task_type,
            preset=preset_name,
            model=selected_model,
            status="running",
            prompt=user_prompt,
        )
        db.add(llm_task)
        db.commit()
        db.refresh(llm_task)

        try:
            response = await self.llm_client.generate_text(
                model=selected_model,
                system_prompt=preset.system_prompt,
                user_prompt=user_prompt,
            )
            generated = response.get("choices", [{}])[0].get("message", {}).get("content", "")
            llm_task.result = generated
            llm_task.status = "success"
            self._apply_result_to_draft(draft, task_type, generated)
            db.commit()
            db.refresh(llm_task)
            return LLMTaskResult(task=llm_task, applied_to_draft=True)
        except Exception as exc:
            llm_task.status = "error"
            llm_task.error = str(exc)
            db.commit()
            db.refresh(llm_task)
            return LLMTaskResult(task=llm_task, applied_to_draft=False)

    @staticmethod
    def _apply_result_to_draft(draft: ArticleDraft, task_type: str, generated: str) -> None:
        if not generated:
            return
        if task_type in {"summary", "rewrite"}:
            draft.content_translated = generated
            return
        if task_type == "title_hashtags":
            title, hashtags = LLMTaskService._parse_title_hashtags(generated)
            if title:
                draft.title_translated = title
            if hashtags:
                current = draft.content_translated or ""
                draft.content_translated = f"{current}\n\n{hashtags}".strip()

    @staticmethod
    def _parse_title_hashtags(generated: str) -> tuple[str, str]:
        title = ""
        hashtags = []
        for line in generated.splitlines():
            if not title and line.strip():
                title = line.strip()
                continue
            hashtags.extend(re.findall(r"#\w+", line))
        return title, " ".join(dict.fromkeys(hashtags))

