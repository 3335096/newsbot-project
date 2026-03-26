from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.db.models.base import Base
from app.db.models.moderation_rule import ModerationRule
from app.services.moderation_service import ModerationService


def _db_session() -> Session:
    engine = create_engine("sqlite:///:memory:", future=True)
    Base.metadata.create_all(bind=engine)
    testing_session = sessionmaker(bind=engine, autocommit=False, autoflush=False, future=True)
    return testing_session()


def test_domain_rule_blocks_article() -> None:
    db = _db_session()
    db.add(
        ModerationRule(
            kind="domain_blacklist",
            pattern="example\\.com",
            action="block",
            enabled=True,
            comment="blocked domain",
        )
    )
    db.commit()

    service = ModerationService(db)
    outcome = service.evaluate_article(
        url="https://example.com/news/1",
        title="News",
        content="Some content",
    )

    assert outcome.blocked is True
    assert outcome.flagged is True
    assert len(outcome.flags) == 1
    assert outcome.flags[0]["action"] == "block"


def test_keyword_rule_flags_article() -> None:
    db = _db_session()
    db.add(
        ModerationRule(
            kind="keyword_blacklist",
            pattern="bitcoin",
            action="flag",
            enabled=True,
        )
    )
    db.commit()

    service = ModerationService(db)
    outcome = service.evaluate_article(
        url="https://news.site/article",
        title="Market",
        content="Bitcoin grows",
    )

    assert outcome.blocked is False
    assert outcome.flagged is True
    assert len(outcome.flags) == 1
    assert outcome.flags[0]["kind"] == "keyword_blacklist"


def test_create_and_toggle_rule() -> None:
    db = _db_session()
    service = ModerationService(db)

    rule = service.create_rule(
        kind="keyword_blacklist",
        pattern="spam",
        action="flag",
        enabled=True,
        comment="test rule",
    )
    assert rule.id is not None
    assert rule.enabled is True

    toggled = service.toggle_rule(rule.id)
    assert toggled.enabled is False
