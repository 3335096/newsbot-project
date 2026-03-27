from sqlalchemy import create_engine

from app.db import models  # noqa: F401
from app.db.models.base import Base
from core.config import settings


def init_db() -> None:
    engine = create_engine(settings.DATABASE_URL, future=True)
    Base.metadata.create_all(bind=engine)
    print("Database initialized successfully!")


if __name__ == "__main__":
    init_db()
