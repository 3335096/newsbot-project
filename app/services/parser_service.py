from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import re
import time
from typing import Any

import feedparser
import httpx
from bs4 import BeautifulSoup
from loguru import logger
from readability import Document
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.db.models.article_raw import ArticleRaw
from app.db.models.source import Source

try:
    from trafilatura import extract as trafilatura_extract
except Exception:  # pragma: no cover - optional fallback
    trafilatura_extract = None


class ParserService:
    def __init__(self, timeout_seconds: int = 30, translation_service: Any | None = None):
        self.timeout_seconds = timeout_seconds
        self.translation_service = translation_service
        if self.translation_service is None:
            try:
                from app.services.translation_service import TranslationService

                self.translation_service = TranslationService()
            except Exception as exc:  # pragma: no cover - env-specific bootstrap fallback
                logger.warning("Translation service unavailable at startup: {}", exc)
                self.translation_service = None

    async def fetch_rss(self, url: str) -> list[dict[str, Any]]:
        async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
            response = await client.get(url)
            response.raise_for_status()

        feed = feedparser.parse(response.text)
        entries: list[dict[str, Any]] = []
        for entry in feed.entries:
            raw_published = (
                getattr(entry, "published_parsed", None)
                or getattr(entry, "updated_parsed", None)
            )
            published_at = self._parsed_time_to_datetime(raw_published)
            entries.append(
                {
                    "url": getattr(entry, "link", ""),
                    "title": getattr(entry, "title", None),
                    "summary": getattr(entry, "summary", None),
                    "published_at": published_at,
                    "author": getattr(entry, "author", None),
                }
            )
        return entries

    async def fetch_html(self, url: str) -> str:
        async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
            response = await client.get(url)
            response.raise_for_status()
        return response.text

    def extract_content(
        self, html: str, extraction_rules: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        extraction_rules = extraction_rules or {}
        soup = BeautifulSoup(html, "lxml")

        title = self._extract_title(soup, extraction_rules)
        content = self._extract_body(html, soup, extraction_rules)
        images = self._extract_images(soup, extraction_rules)

        return {
            "title": title,
            "content": content,
            "media": [{"url": image, "type": "image"} for image in images],
        }

    def detect_language(self, text: str) -> str:
        cleaned = self.normalize_text(text)
        if not cleaned:
            return "unknown"

        cyrillic = len(re.findall(r"[А-Яа-яЁё]", cleaned))
        latin = len(re.findall(r"[A-Za-z]", cleaned))
        if cyrillic == 0 and latin == 0:
            return "unknown"
        if cyrillic > latin:
            return "ru"
        if latin > cyrillic:
            return "en"
        return "unknown"

    def normalize_text(self, text: str) -> str:
        text = re.sub(r"<[^>]+>", " ", text)
        text = text.replace("\u00a0", " ")
        text = re.sub(r"\s+", " ", text)
        return text.strip().lower()

    def compute_hash(self, content: str) -> str:
        normalized = self.normalize_text(content)
        return hashlib.sha256(normalized.encode("utf-8")).hexdigest()

    def upsert_article_raw(
        self,
        db: Session,
        *,
        source_id: int,
        url: str,
        title_raw: str | None,
        content_raw: str | None,
        media: list[dict[str, Any]] | None,
        published_at: datetime | None,
        language_detected: str | None,
        hash_original: str,
    ) -> tuple[ArticleRaw, bool]:
        existing = (
            db.query(ArticleRaw)
            .filter(
                or_(
                    ArticleRaw.url == url,
                    (ArticleRaw.source_id == source_id)
                    & (ArticleRaw.hash_original == hash_original),
                )
            )
            .first()
        )
        if existing:
            return existing, False

        article = ArticleRaw(
            source_id=source_id,
            url=url,
            title_raw=title_raw,
            content_raw=content_raw,
            media=media,
            published_at=published_at,
            language_detected=language_detected,
            hash_original=hash_original,
        )
        db.add(article)
        db.commit()
        db.refresh(article)
        return article, True

    async def process_source(self, db: Session, source: Source) -> dict[str, int]:
        if source.type != "rss":
            logger.info("Source {} has unsupported type {} for MVP", source.id, source.type)
            return {"processed": 0, "created": 0, "drafts_created": 0}

        entries = await self.fetch_rss(source.url)
        processed = 0
        created = 0
        drafts_created = 0

        for entry in entries:
            if not entry["url"]:
                continue

            processed += 1
            title = entry["title"]
            content = entry.get("summary") or ""
            media: list[dict[str, Any]] = []

            try:
                html = await self.fetch_html(entry["url"])
                extracted = self.extract_content(html, source.extraction_rules or {})
                title = extracted.get("title") or title
                content = extracted.get("content") or content
                media = extracted.get("media") or []
            except Exception as exc:  # pragma: no cover - network and site variance
                logger.warning("Failed to parse article url={}: {}", entry["url"], exc)

            lang = self.detect_language(f"{title or ''}\n{content}")
            content_hash = self.compute_hash(f"{title or ''}\n{content}")

            article, is_created = self.upsert_article_raw(
                db,
                source_id=source.id,
                url=entry["url"],
                title_raw=title,
                content_raw=content,
                media=media,
                published_at=entry.get("published_at"),
                language_detected=lang,
                hash_original=content_hash,
            )
            if is_created:
                created += 1
            if source.translate_enabled and self.translation_service is not None:
                _, draft_created = await self.translation_service.get_or_create_draft_for_article(
                    db,
                    article,
                    target_language=source.default_target_language,
                )
                if draft_created:
                    drafts_created += 1

        return {"processed": processed, "created": created, "drafts_created": drafts_created}

    @staticmethod
    def _parsed_time_to_datetime(parsed_struct: time.struct_time | None) -> datetime | None:
        if not parsed_struct:
            return None
        return datetime.fromtimestamp(time.mktime(parsed_struct), tz=timezone.utc)

    @staticmethod
    def _extract_title(soup: BeautifulSoup, extraction_rules: dict[str, Any]) -> str | None:
        title_selector = extraction_rules.get("title_css")
        if title_selector:
            selected = soup.select_one(title_selector)
            if selected:
                title = selected.get_text(" ", strip=True)
                if title:
                    return title

        title_tag = soup.find("title")
        if title_tag:
            return title_tag.get_text(" ", strip=True)
        return None

    @staticmethod
    def _extract_body(html: str, soup: BeautifulSoup, extraction_rules: dict[str, Any]) -> str:
        content_selector = extraction_rules.get("content_css")
        if content_selector:
            selected = soup.select_one(content_selector)
            if selected:
                return selected.get_text(" ", strip=True)

        if trafilatura_extract:
            extracted = trafilatura_extract(html, include_images=False, include_formatting=False)
            if extracted:
                return extracted

        readability_doc = Document(html)
        readability_html = readability_doc.summary()
        readability_text = BeautifulSoup(readability_html, "lxml").get_text(" ", strip=True)
        return readability_text

    @staticmethod
    def _extract_images(soup: BeautifulSoup, extraction_rules: dict[str, Any]) -> list[str]:
        image_selector = extraction_rules.get("image_css")
        if image_selector:
            candidates = [img.get("src") for img in soup.select(image_selector)]
        else:
            candidates = [img.get("src") for img in soup.find_all("img")]
        return [c for c in candidates if c]
