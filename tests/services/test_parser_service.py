from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.db.models.article_draft import ArticleDraft
from app.db.models.article_raw import ArticleRaw
from app.db.models.base import Base
from app.db.models.source import Source
from app.services.parser_service import ParserService
from app.services.translation_service import TranslationService


def _db_session() -> Session:
    engine = create_engine("sqlite:///:memory:", future=True)
    Base.metadata.create_all(bind=engine)
    testing_session = sessionmaker(bind=engine, autocommit=False, autoflush=False, future=True)
    return testing_session()


def test_compute_hash_is_stable_for_semantically_same_text() -> None:
    parser = ParserService()
    left = "Hello   world\n\nThis is   content."
    right = "hello world this is content."

    assert parser.compute_hash(left) == parser.compute_hash(right)


def test_detect_language_ru_en_unknown() -> None:
    parser = ParserService()

    assert parser.detect_language("Это русскоязычный текст") == "ru"
    assert parser.detect_language("This is an english text") == "en"
    assert parser.detect_language("12345 !!!") == "unknown"


def test_extract_content_with_css_rules() -> None:
    parser = ParserService()
    html = """
    <html>
      <head><title>Fallback title</title></head>
      <body>
        <h1 class="my-title">Actual title</h1>
        <article class="main-body">Main body text</article>
        <img class="hero" src="https://example.com/img.png" />
      </body>
    </html>
    """

    result = parser.extract_content(
        html,
        extraction_rules={
            "title_css": ".my-title",
            "content_css": ".main-body",
            "image_css": ".hero",
        },
    )

    assert result["title"] == "Actual title"
    assert "Main body text" in result["content"]
    assert result["media"] == [{"url": "https://example.com/img.png", "type": "image"}]


def test_upsert_article_raw_deduplicates_by_url_and_hash() -> None:
    parser = ParserService()
    db = _db_session()
    source = Source(name="s1", type="rss", url="https://example.com/feed.xml")
    db.add(source)
    db.commit()
    db.refresh(source)

    article, created = parser.upsert_article_raw(
        db,
        source_id=source.id,
        url="https://example.com/article-1",
        title_raw="t1",
        content_raw="c1",
        media=[],
        published_at=datetime.now(timezone.utc),
        language_detected="en",
        hash_original=parser.compute_hash("c1"),
    )
    assert created is True
    assert article.id is not None

    duplicate_by_url, created_2 = parser.upsert_article_raw(
        db,
        source_id=source.id,
        url="https://example.com/article-1",
        title_raw="t2",
        content_raw="c2",
        media=[],
        published_at=None,
        language_detected="en",
        hash_original=parser.compute_hash("c2"),
    )
    assert created_2 is False
    assert duplicate_by_url.id == article.id

    duplicate_by_hash, created_3 = parser.upsert_article_raw(
        db,
        source_id=source.id,
        url="https://example.com/article-2",
        title_raw="t3",
        content_raw="c1",
        media=[],
        published_at=None,
        language_detected="en",
        hash_original=parser.compute_hash("c1"),
    )
    assert created_3 is False
    assert duplicate_by_hash.id == article.id

    count = db.query(ArticleRaw).count()
    assert count == 1


def test_translation_cache_creates_second_draft_without_llm_call() -> None:
    db = _db_session()
    source = Source(name="s1", type="rss", url="https://example.com/feed.xml")
    db.add(source)
    db.commit()
    db.refresh(source)

    article_one = ArticleRaw(
        source_id=source.id,
        url="https://example.com/article-1",
        title_raw="Hello",
        content_raw="World",
        media=[],
        language_detected="en",
        hash_original="same_hash",
    )
    article_two = ArticleRaw(
        source_id=source.id,
        url="https://example.com/article-2",
        title_raw="Hello2",
        content_raw="World2",
        media=[],
        language_detected="en",
        hash_original="same_hash",
    )
    db.add(article_one)
    db.add(article_two)
    db.commit()
    db.refresh(article_one)
    db.refresh(article_two)

    service = TranslationService()

    async def fake_translate_text(**kwargs):
        return {
            "title_translated": "Привет",
            "content_translated": "Мир",
            "translation_engine": "openrouter:test-model",
            "translation_preset": "translation_editorial",
        }

    service.translate_text = fake_translate_text  # type: ignore[method-assign]

    import asyncio

    first_draft, first_created = asyncio.run(
        service.get_or_create_draft_for_article(
            db,
            article_one,
            target_language="ru",
            model="test-model",
        )
    )
    assert first_created is True
    assert first_draft.title_translated == "Привет"

    second_draft, second_created = asyncio.run(
        service.get_or_create_draft_for_article(
            db,
            article_two,
            target_language="ru",
            model="test-model",
        )
    )
    assert second_created is True
    assert second_draft.title_translated == "Привет"
    assert second_draft.content_translated == "Мир"

    drafts_count = db.query(ArticleDraft).count()
    assert drafts_count == 2

