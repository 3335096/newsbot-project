from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.db.models.article_draft import ArticleDraft
from app.db.models.base import Base
from app.db.models.moderation_rule import ModerationRule
from app.db.models.source import Source
from app.metrics import PARSER_EVENTS_TOTAL
from app.services.parser_service import ParserService


def _db_session() -> Session:
    engine = create_engine("sqlite:///:memory:", future=True)
    Base.metadata.create_all(bind=engine)
    testing_session = sessionmaker(bind=engine, autocommit=False, autoflush=False, future=True)
    return testing_session()


def _counter_value(event: str) -> float:
    return PARSER_EVENTS_TOTAL.labels(event=event)._value.get()


class _FakeTranslationService:
    async def get_or_create_draft_for_article(
        self,
        db: Session,
        article: Any,
        *,
        target_language: str,
        model: str = "unused",
        preset: str | None = None,
    ):
        draft = ArticleDraft(
            article_raw_id=article.id,
            target_language=target_language,
            title_translated="Перевод заголовка",
            content_translated="Перевод текста",
            translation_engine="openrouter:test-model",
            translation_preset="translation_editorial",
            status="new",
            media=article.media,
        )
        db.add(draft)
        db.commit()
        db.refresh(draft)
        return draft, True


def test_process_source_blocks_article_and_increments_blocked_metric() -> None:
    db = _db_session()
    source = Source(
        name="test-source",
        type="rss",
        url="https://example.com/feed.xml",
        translate_enabled=True,
        default_target_language="ru",
    )
    db.add(source)
    db.add(
        ModerationRule(
            kind="keyword_blacklist",
            pattern="crypto scam",
            action="block",
            enabled=True,
        )
    )
    db.commit()
    db.refresh(source)

    parser = ParserService(translation_service=_FakeTranslationService())

    async def fake_fetch_rss(url: str) -> list[dict[str, Any]]:
        return [
            {
                "url": "https://example.com/news/1",
                "title": "Breaking news",
                "summary": "Potential crypto scam was detected",
                "published_at": datetime.now(timezone.utc),
                "author": "author",
            }
        ]

    async def fake_fetch_html(url: str) -> str:
        return "<html><head><title>Breaking news</title></head><body>Potential crypto scam was detected</body></html>"

    parser.fetch_rss = fake_fetch_rss  # type: ignore[method-assign]
    parser.fetch_html = fake_fetch_html  # type: ignore[method-assign]

    before_blocked = _counter_value("blocked")
    before_processed = _counter_value("processed")

    stats = asyncio.run(parser.process_source(db, source))

    assert stats["processed"] == 1
    assert stats["created"] == 1
    assert stats["drafts_created"] == 0
    assert db.query(ArticleDraft).count() == 0
    assert _counter_value("blocked") == before_blocked + 1
    assert _counter_value("processed") == before_processed + 1


def test_process_source_flags_article_sets_draft_flagged_and_metrics() -> None:
    db = _db_session()
    source = Source(
        name="test-source",
        type="rss",
        url="https://example.com/feed.xml",
        translate_enabled=True,
        default_target_language="ru",
    )
    db.add(source)
    db.add(
        ModerationRule(
            kind="keyword_blacklist",
            pattern="bitcoin",
            action="flag",
            enabled=True,
        )
    )
    db.commit()
    db.refresh(source)

    parser = ParserService(translation_service=_FakeTranslationService())

    async def fake_fetch_rss(url: str) -> list[dict[str, Any]]:
        return [
            {
                "url": "https://example.com/news/2",
                "title": "Market update",
                "summary": "Bitcoin is up this week",
                "published_at": datetime.now(timezone.utc),
                "author": "author",
            }
        ]

    async def fake_fetch_html(url: str) -> str:
        return "<html><head><title>Market update</title></head><body>Bitcoin is up this week</body></html>"

    parser.fetch_rss = fake_fetch_rss  # type: ignore[method-assign]
    parser.fetch_html = fake_fetch_html  # type: ignore[method-assign]

    before_flagged = _counter_value("flagged")
    before_drafts = _counter_value("drafts_created")

    stats = asyncio.run(parser.process_source(db, source))

    assert stats["processed"] == 1
    assert stats["created"] == 1
    assert stats["drafts_created"] == 1

    draft = db.query(ArticleDraft).one()
    assert draft.status == "flagged"
    assert draft.flags
    assert any(flag.get("action") == "flag" for flag in draft.flags)
    assert _counter_value("flagged") == before_flagged + 1
    assert _counter_value("drafts_created") == before_drafts + 1
