from sqlalchemy import ForeignKey, JSON, Numeric, Text, text
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, TimestampMixin


class ArticleDraft(Base, TimestampMixin):
    __tablename__ = "articles_draft"
    id: Mapped[int] = mapped_column(primary_key=True)
    article_raw_id: Mapped[int | None] = mapped_column(ForeignKey("articles_raw.id", ondelete="CASCADE"))
    target_language: Mapped[str] = mapped_column(
        Text, nullable=False, default="ru", server_default=text("'ru'")
    )
    title_translated: Mapped[str | None] = mapped_column(Text)
    content_translated: Mapped[str | None] = mapped_column(Text)
    translation_engine: Mapped[str | None] = mapped_column(Text)
    translation_preset: Mapped[str | None] = mapped_column(Text)
    translation_quality_score: Mapped[float | None] = mapped_column(Numeric)
    status: Mapped[str] = mapped_column(
        Text, nullable=False, default="new", server_default=text("'new'")
    )
    rejection_reason: Mapped[str | None] = mapped_column(Text)
    flags: Mapped[dict | None] = mapped_column(JSON)
    media: Mapped[dict | None] = mapped_column(JSON)
