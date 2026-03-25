import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from core.config import settings
from app.db.models.base import Base
from app.db import models  # noqa: F401

async def init_db():
    engine = create_async_engine(settings.DATABASE_URL.replace("+psycopg2", "+asyncpg"))
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    print("Database initialized successfully!")

if __name__ == "__main__":
    asyncio.run(init_db())
