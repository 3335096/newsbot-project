from datetime import datetime

from sqlalchemy import BigInteger, ForeignKey, TIMESTAMP, Text, text
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class Publication(Base):
    __tablename__ = "publications"
    id: Mapped[int] = mapped_column(primary_key=True)
    draft_id: Mapped[int | None] = mapped_column(ForeignKey("articles_draft.id", ondelete="SET NULL"))
    channel_id: Mapped[int | None] = mapped_column(BigInteger)
    channel_alias: Mapped[str | None] = mapped_column(Text)
    message_id: Mapped[int | None] = mapped_column(BigInteger)
    status: Mapped[str] = mapped_column(
        Text, nullable=False, default="queued", server_default=text("'queued'")
    )
    scheduled_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))
    published_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))
    target_language: Mapped[str] = mapped_column(Text, nullable=False, default="ru", server_default=text("'ru'"))
    log: Mapped[str | None] = mapped_column(Text)
