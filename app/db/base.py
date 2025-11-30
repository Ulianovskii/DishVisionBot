# app/db/base.py

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import declarative_base

from app.config import settings

Base = declarative_base()

# URL БД берём из настроек / .env
# Пример: postgresql+asyncpg://user:password@localhost:5432/dishvision
DATABASE_URL = settings.database_url

engine = create_async_engine(
    DATABASE_URL,
    echo=False,
    future=True,
)

AsyncSessionLocal = async_sessionmaker(
    engine,
    expire_on_commit=False,
    class_=AsyncSession,
)


async def init_db() -> None:
    """
    Инициализирует БД: создаёт таблицы из app/db/models.py.
    """
    # важно: просто импортируем файл с моделями, чтобы они зарегистрировались в Base.metadata
    from app.db import models  # noqa: F401

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
