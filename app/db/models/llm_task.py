from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import Text, ForeignKey, TIMESTAMP, Numeric, Integer
from datetime import datetime
from .base import Base

class LLMTask(Base):
    __tablename__ = "llm_tasks"
    id: Mapped[int] = mapped_column(primary_key=True)
    draft_id: Mapped[int | None] = mapped_column(ForeignKey("articles_draft.id", ondelete="CASCADE"))
    task_type: Mapped[str] = mapped_column(Text)  # translation/summary/rewrite/title/hashtags
    preset: Mapped[str | None] = mapped_column(Text)
    model: Mapped[str | None] = mapped_column(Text)
    prompt: Mapped[str | None] = mapped_column(Text)
    response: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(Text, default="pending")  # pending/completed/failed
    started_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))
    duration_ms: Mapped[int | None] = mapped_column(Integer)
    tokens_used: Mapped[int | None] = mapped_column(Integer)
    cost: Mapped[float | None] = mapped_column(Numeric(10, 6))
