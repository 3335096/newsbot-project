from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.db.models.article_draft import ArticleDraft
from app.db.models.publication import Publication
from app.db.models.source import Source
from app.db.models.base import Base
from app.services.queue_dispatcher import enqueue_due_publications, enqueue_publication


def _db_session() -> Session:
    engine = create_engine("sqlite:///:memory:", future=True)
    Base.metadata.create_all(bind=engine)
    testing_session = sessionmaker(bind=engine, autocommit=False, autoflush=False, future=True)
    return testing_session()


class _FakeQueue:
    def __init__(self) -> None:
        self.calls: list[tuple[str, tuple, dict]] = []

    class _Job:
        def __init__(self, job_id: str):
            self.id = job_id

    def enqueue(self, fn: str, *args, **kwargs):
        self.calls.append((fn, args, kwargs))
        return self._Job(job_id=f"job-{len(self.calls)}")


def _seed_draft(db: Session) -> ArticleDraft:
    source = Source(name="s1", type="rss", url="https://example.com/feed.xml")
    db.add(source)
    db.commit()
    db.refresh(source)

    draft = ArticleDraft(
        article_raw_id=None,
        target_language="ru",
        title_translated="title",
        content_translated="content",
        status="approved",
    )
    db.add(draft)
    db.commit()
    db.refresh(draft)
    return draft


def test_enqueue_due_publications_enqueues_queued_and_due_scheduled() -> None:
    db = _db_session()
    draft = _seed_draft(db)
    now = datetime.now(timezone.utc)

    p_queued = Publication(
        draft_id=draft.id,
        channel_id=123,
        channel_alias="main",
        status="queued",
        target_language="ru",
    )
    p_due = Publication(
        draft_id=draft.id,
        channel_id=124,
        channel_alias="backup",
        status="scheduled",
        scheduled_at=now - timedelta(minutes=1),
        target_language="ru",
    )
    p_future = Publication(
        draft_id=draft.id,
        channel_id=125,
        channel_alias="later",
        status="scheduled",
        scheduled_at=now + timedelta(minutes=10),
        target_language="ru",
    )
    db.add_all([p_queued, p_due, p_future])
    db.commit()

    queue = _FakeQueue()
    enqueued = enqueue_due_publications(db, queue=queue)

    assert enqueued == 2
    assert len(queue.calls) == 2
    db.refresh(p_queued)
    db.refresh(p_due)
    db.refresh(p_future)
    assert p_queued.queue_job_id
    assert p_due.queue_job_id
    assert p_future.queue_job_id is None


def test_enqueue_publication_force_requeue_allows_retry() -> None:
    db = _db_session()
    draft = _seed_draft(db)
    publication = Publication(
        draft_id=draft.id,
        channel_id=321,
        channel_alias="main",
        status="queued",
        target_language="ru",
    )
    db.add(publication)
    db.commit()
    db.refresh(publication)

    queue = _FakeQueue()
    first_job = enqueue_publication(db, publication, queue=queue)
    assert first_job is not None
    db.refresh(publication)
    first_job_id = publication.queue_job_id
    assert first_job_id

    skipped_job = enqueue_publication(db, publication, queue=queue, force=False)
    assert skipped_job is None
    db.refresh(publication)
    assert publication.queue_job_id == first_job_id

    forced_job = enqueue_publication(db, publication, queue=queue, force=True)
    assert forced_job is not None
    db.refresh(publication)
    assert publication.queue_job_id != first_job_id
