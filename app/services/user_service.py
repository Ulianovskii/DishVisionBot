# app/services/user_service.py

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import AsyncSessionLocal
from app.db.models import User
from app.db.repositories.user_repository import UserRepository


async def get_or_create_user(telegram_id: int) -> User:
    """
    Гарантируем, что пользователь есть в БД.
    Если уже есть — вернём.
    Если нет — создадим.
    """
    async with AsyncSessionLocal() as session:  # type: AsyncSession
        repo = UserRepository(session=session)

        user = await repo.get_by_telegram_id(telegram_id)
        if user is not None:
            return user

        user = await repo.create_user(telegram_id=telegram_id)
        await session.commit()
        return user
