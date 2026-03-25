from sqlalchemy import JSON, BigInteger, CheckConstraint, Text
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, TimestampMixin


class User(Base, TimestampMixin):
    __tablename__ = "users"
    __table_args__ = (
        CheckConstraint("role IN ('admin','editor')", name="user_role_valid"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    telegram_user_id: Mapped[int] = mapped_column(BigInteger, unique=True, nullable=False)
    role: Mapped[str] = mapped_column(Text, nullable=False)
    display_name: Mapped[str | None] = mapped_column(Text)
    settings: Mapped[dict | None] = mapped_column(JSON)
