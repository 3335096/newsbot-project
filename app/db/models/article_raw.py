from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import Text, JSON, ForeignKey, TIMESTAMP
from datetime import datetime
from .base import Base

class ArticlesRaw(Base):
    __tablename__ = "articles_raw"
    id: Mapped[int] = mapped_column(primary_key=True)
    source_id: Mapped[int | None] = mapped_column(ForeignKey("source.id"))
    url: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    title_raw: Mapped[str | None] = mapped_column(Text)
    content_raw: Mapped[str | None] = mapped_column(Text)
    media: Mapped[dict | None] = mapped_column(JSON)
    published_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))
    fetched_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True))
    language_detected: Mapped[str | None] = mapped_column(Text)
    hash_original: Mapped[str] = mapped_column(Text, nullable=False)
