from sqlalchemy import JSON, Boolean, CheckConstraint, Text, text
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, TimestampMixin

class Source(Base, TimestampMixin):
    __tablename__ = "sources"
    __table_args__ = (
        CheckConstraint("type IN ('rss','site')", name="source_type_valid"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    type: Mapped[str] = mapped_column(Text, nullable=False)  # 'rss' | 'site'
    url: Mapped[str] = mapped_column(Text, nullable=False)
    enabled: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default=text("true")
    )
    schedule_cron: Mapped[str | None] = mapped_column(Text, nullable=True)
    translate_enabled: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default=text("true")
    )
    default_target_language: Mapped[str] = mapped_column(
        Text, nullable=False, default="ru", server_default=text("'ru'")
    )
    extraction_rules: Mapped[dict | None] = mapped_column(JSON, nullable=True)
