import asyncio

from sqlalchemy.ext.asyncio import create_async_engine

from app.db import models  # noqa: F401
from app.db.models.base import Base
from core.config import settings

async def init_db():
    engine = create_async_engine(settings.DATABASE_URL.replace("+psycopg2", "+asyncpg"))
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    print("Database initialized successfully!")

if __name__ == "__main__":
    asyncio.run(init_db())
