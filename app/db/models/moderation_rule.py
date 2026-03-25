from sqlalchemy import Boolean, Text, text
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class ModerationRule(Base):
    __tablename__ = "moderation_rules"
    id: Mapped[int] = mapped_column(primary_key=True)
    kind: Mapped[str] = mapped_column(Text, nullable=False)  # domain_blacklist/keyword_blacklist
    pattern: Mapped[str] = mapped_column(Text, nullable=False)
    action: Mapped[str] = mapped_column(Text, nullable=False)  # block/flag
    enabled: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default=text("true")
    )
    comment: Mapped[str | None] = mapped_column(Text)
