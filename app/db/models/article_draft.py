from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import Text, JSON, ForeignKey
from .base import Base, TimestampMixin

class ArticlesDraft(Base, TimestampMixin):
    __tablename__ = "articles_draft"
    id: Mapped[int] = mapped_column(primary_key=True)
    article_raw_id: Mapped[int | None] = mapped_column(ForeignKey("articles_raw.id", ondelete="CASCADE"))
    target_language: Mapped[str] = mapped_column(Text, default="ru")
    title_translated: Mapped[str | None] = mapped_column(Text)
    content_translated: Mapped[str | None] = mapped_column(Text)
    translation_engine: Mapped[str | None] = mapped_column(Text)
    translation_preset: Mapped[str | None] = mapped_column(Text)
    translation_quality_score: Mapped[float | None] = mapped_column()
    status: Mapped[str] = mapped_column(Text, default="new")  # new/flagged/approved/rejected/published
    rejection_reason: Mapped[str | None] = mapped_column(Text)
    flags: Mapped[dict | None] = mapped_column(JSON)
    media: Mapped[dict | None] = mapped_column(JSON)
