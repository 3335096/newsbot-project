from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import Text, JSON, ForeignKey, TIMESTAMP
from datetime import datetime
from .base import Base, TimestampMixin

class Publication(Base, TimestampMixin):
    __tablename__ = "publications"
    id: Mapped[int] = mapped_column(primary_key=True)
    draft_id: Mapped[int | None] = mapped_column(ForeignKey("articles_draft.id", ondelete="CASCADE"))
    channel_id: Mapped[str] = mapped_column(Text, nullable=False)
    message_id: Mapped[int] = mapped_column(nullable=False)
    published_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), default=datetime.now)
    status: Mapped[str] = mapped_column(Text, default="published")  # published/edited/deleted
    metadata_: Mapped[dict | None] = mapped_column(JSON, name="metadata")
