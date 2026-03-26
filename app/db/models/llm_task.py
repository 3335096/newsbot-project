from sqlalchemy import ForeignKey, Integer, Numeric, Text, text
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, TimestampMixin


class LLMTask(Base, TimestampMixin):
    __tablename__ = "llm_tasks"
    id: Mapped[int] = mapped_column(primary_key=True)
    draft_id: Mapped[int | None] = mapped_column(ForeignKey("articles_draft.id", ondelete="CASCADE"))
    task_type: Mapped[str] = mapped_column(Text, nullable=False)  # translation/summary/rewrite/title/hashtags
    preset: Mapped[str | None] = mapped_column(Text)
    model: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(
        Text, nullable=False, default="queued", server_default=text("'queued'")
    )
    queue_job_id: Mapped[str | None] = mapped_column(Text)
    prompt: Mapped[str | None] = mapped_column(Text)
    result: Mapped[str | None] = mapped_column(Text)
    tokens_in: Mapped[int | None] = mapped_column(Integer)
    tokens_out: Mapped[int | None] = mapped_column(Integer)
    cost_usd: Mapped[float | None] = mapped_column(Numeric(10, 4))
    error: Mapped[str | None] = mapped_column(Text)
