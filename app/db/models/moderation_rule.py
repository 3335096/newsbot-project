from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import Text, Boolean, JSON
from .base import Base, TimestampMixin

class ModerationRule(Base, TimestampMixin):
    __tablename__ = "moderation_rules"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    description: Mapped[str | None] = mapped_column(Text)
    rule_type: Mapped[str] = mapped_column(Text)  # keyword/regex/llm
    pattern: Mapped[str | None] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    action: Mapped[str] = mapped_column(Text)  # flag/reject
    severity: Mapped[str] = mapped_column(Text, default="medium")  # low/medium/high
    metadata_: Mapped[dict | None] = mapped_column(JSON, name="metadata")
