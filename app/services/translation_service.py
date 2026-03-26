from __future__ import annotations

from sqlalchemy.orm import Session

from app.db.models.article_draft import ArticleDraft
from app.db.models.article_raw import ArticleRaw
from app.services.llm_client import LLMClient
from core.config import settings


class TranslationService:
    def __init__(self):
        self.llm_client = LLMClient()
        self.default_preset = "translation_editorial"

    async def translate_text(
        self,
        *,
        title: str | None,
        content: str | None,
        source_language: str | None,
        target_language: str = settings.DEFAULT_TARGET_LANGUAGE,
        model: str = settings.LLM_DEFAULT_MODEL_TRANSLATE,
        preset: str | None = None,
    ) -> dict[str, str]:
        source_language = source_language or "unknown"
        normalized_title = title or ""
        normalized_content = content or ""
        used_preset = preset or self.default_preset

        # If source and target are equal or text is empty, keep original content.
        if not normalized_content.strip() or source_language == target_language:
            return {
                "title_translated": normalized_title,
                "content_translated": normalized_content,
                "translation_engine": f"openrouter:{model}",
                "translation_preset": used_preset,
            }

        system_prompt = (
            "Ты — профессиональный редактор-переводчик новостей. "
            "Сохраняй факты, числа, имена и нейтральный стиль."
        )
        user_prompt = (
            f"Переведи текст с {source_language} на {target_language}.\n"
            "Верни ответ строго в формате:\n"
            "TITLE: <переведенный заголовок>\n"
            "CONTENT: <переведенный текст>\n\n"
            f"TITLE:\n{normalized_title}\n\n"
            f"CONTENT:\n{normalized_content}"
        )

        response = await self.llm_client.generate_text(
            model=model,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
        )
        generated = response.get("choices", [{}])[0].get("message", {}).get("content", "")
        parsed = self._parse_translation_response(generated, normalized_title, normalized_content)
        parsed["translation_engine"] = f"openrouter:{model}"
        parsed["translation_preset"] = used_preset
        return parsed

    async def get_or_create_draft_for_article(
        self,
        db: Session,
        article: ArticleRaw,
        *,
        target_language: str = settings.DEFAULT_TARGET_LANGUAGE,
        model: str = settings.LLM_DEFAULT_MODEL_TRANSLATE,
        preset: str | None = None,
    ) -> tuple[ArticleDraft, bool]:
        existing_draft = (
            db.query(ArticleDraft)
            .filter(
                ArticleDraft.article_raw_id == article.id,
                ArticleDraft.target_language == target_language,
            )
            .first()
        )
        if existing_draft:
            return existing_draft, False

        # Translation cache by source hash + target language + model + preset.
        cached_translation = (
            db.query(ArticleDraft)
            .join(ArticleRaw, ArticleRaw.id == ArticleDraft.article_raw_id)
            .filter(
                ArticleRaw.hash_original == article.hash_original,
                ArticleDraft.target_language == target_language,
                ArticleDraft.translation_engine == f"openrouter:{model}",
                ArticleDraft.translation_preset == (preset or self.default_preset),
            )
            .first()
        )

        if cached_translation:
            title_translated = cached_translation.title_translated
            content_translated = cached_translation.content_translated
            translation_engine = cached_translation.translation_engine
            translation_preset = cached_translation.translation_preset
        else:
            translated = await self.translate_text(
                title=article.title_raw,
                content=article.content_raw,
                source_language=article.language_detected,
                target_language=target_language,
                model=model,
                preset=preset,
            )
            title_translated = translated["title_translated"]
            content_translated = translated["content_translated"]
            translation_engine = translated["translation_engine"]
            translation_preset = translated["translation_preset"]

        draft = ArticleDraft(
            article_raw_id=article.id,
            target_language=target_language,
            title_translated=title_translated,
            content_translated=content_translated,
            translation_engine=translation_engine,
            translation_preset=translation_preset,
            status="new",
            media=article.media,
        )
        db.add(draft)
        db.commit()
        db.refresh(draft)
        return draft, True

    @staticmethod
    def _parse_translation_response(
        generated: str,
        fallback_title: str,
        fallback_content: str,
    ) -> dict[str, str]:
        if not generated:
            return {
                "title_translated": fallback_title,
                "content_translated": fallback_content,
            }

        title = fallback_title
        content = fallback_content
        lines = generated.splitlines()
        content_started = False
        content_lines: list[str] = []
        for line in lines:
            if line.strip().startswith("TITLE:"):
                title = line.split("TITLE:", 1)[1].strip() or fallback_title
                continue
            if line.strip().startswith("CONTENT:"):
                content_started = True
                maybe_content = line.split("CONTENT:", 1)[1].strip()
                if maybe_content:
                    content_lines.append(maybe_content)
                continue
            if content_started:
                content_lines.append(line)

        if content_lines:
            content = "\n".join(content_lines).strip() or fallback_content

        return {
            "title_translated": title,
            "content_translated": content,
        }

