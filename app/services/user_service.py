# app/services/user_service.py

from typing import Optional

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.db.base import AsyncSessionLocal
from app.db.models import User


async def get_user_by_telegram_id(telegram_id: int) -> Optional[User]:
    """
    Найти пользователя по telegram_id или вернуть None.
    """
    async with AsyncSessionLocal() as session:
        stmt = select(User).where(User.telegram_id == telegram_id)
        result = await session.execute(stmt)
        return result.scalar_one_or_none()


async def get_or_create_user(telegram_id: int) -> User:
    """
    Найти пользователя по telegram_id, а если нет — создать.
    """
    async with AsyncSessionLocal() as session:
        stmt = select(User).where(User.telegram_id == telegram_id)
        result = await session.execute(stmt)
        user = result.scalar_one_or_none()

        if user:
            return user

        user = User(telegram_id=telegram_id)
        session.add(user)

        try:
            await session.commit()
        except IntegrityError:
            # На случай гонки двух апдейтов в один момент
            await session.rollback()
            result = await session.execute(
                select(User).where(User.telegram_id == telegram_id)
            )
            user = result.scalar_one()
            return user

        await session.refresh(user)
        return user


async def _is_premium_user(telegram_id: int) -> bool:
    """
    Проверка, является ли пользователь премиумным.
    Смотрим поле `is_premium` в таблице users.
    """
    async with AsyncSessionLocal() as session:
        stmt = select(User.is_premium).where(User.telegram_id == telegram_id)
        result = await session.execute(stmt)
        is_premium = result.scalar_one_or_none()
        return bool(is_premium)
