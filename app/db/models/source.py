from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import Boolean, Text, JSON
from .base import Base, TimestampMixin

class Source(Base, TimestampMixin):
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    type: Mapped[str] = mapped_column(Text, nullable=False)  # 'rss' | 'site'
    url: Mapped[str] = mapped_column(Text, nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    schedule_cron: Mapped[str | None] = mapped_column(Text, nullable=True)
    translate_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    default_target_language: Mapped[str] = mapped_column(Text, default="ru")
    extraction_rules: Mapped[dict | None] = mapped_column(JSON, nullable=True)
