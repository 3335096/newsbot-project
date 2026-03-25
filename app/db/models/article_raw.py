from datetime import datetime

from sqlalchemy import JSON, TIMESTAMP, ForeignKey, Text, UniqueConstraint, text
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class ArticleRaw(Base):
    __tablename__ = "articles_raw"
    __table_args__ = (
        UniqueConstraint("hash_original", "source_id", name="uq_articles_raw_hash_source"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    source_id: Mapped[int | None] = mapped_column(ForeignKey("sources.id"))
    url: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    title_raw: Mapped[str | None] = mapped_column(Text)
    content_raw: Mapped[str | None] = mapped_column(Text)
    media: Mapped[dict | None] = mapped_column(JSON)
    published_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))
    fetched_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=text("now()")
    )
    language_detected: Mapped[str | None] = mapped_column(Text)
    hash_original: Mapped[str] = mapped_column(Text, nullable=False)
