# app/services/limit_service.py

from datetime import date
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.db.base import AsyncSessionLocal
from app.db.models import UserLimit
from app.config_limits import (
    FREE_TARIFF,
    PREMIUM_TARIFF,
)


def get_limits_for_user(is_premium: bool) -> tuple[int, int]:
    """
    Возвращает (daily_analyses_limit, refinements_limit) для тарифа.
    """
    tariff = PREMIUM_TARIFF if is_premium else FREE_TARIFF
    return tariff.daily_photos, tariff.refinements_per_photo


async def _get_or_create_user_limits(
    session,
    user_id: int,
    day: date,
) -> UserLimit:
    """
    Найти или создать запись лимитов на конкретный день.
    """
    stmt = select(UserLimit).where(
        UserLimit.user_id == user_id,
        UserLimit.date == day,
    )
    result = await session.execute(stmt)
    limits: UserLimit | None = result.scalar_one_or_none()

    if limits:
        return limits

    limits = UserLimit(
        user_id=user_id,
        date=day,
        photos_used=0,
        refinements_used=0,
    )
    session.add(limits)

    try:
        await session.commit()
    except IntegrityError:
        # На случай гонки двух запросов одновременно
        await session.rollback()
        result = await session.execute(stmt)
        limits = result.scalar_one()

    return limits


async def consume_photo_quota(
    user_id: int,
    is_premium: bool = False,
) -> tuple[bool, int, int]:
    """
    Пытается списать 1 анализ фото из дневного лимита.

    Возвращает (allowed, used, limit):
      - allowed: True, если лимит не превышен и счётчик увеличен
      - used: сколько анализов уже использовано за день (после операции, если allowed=True)
      - limit: дневной лимит анализов для пользователя
    """
    today = date.today()

    async with AsyncSessionLocal() as session:
        limits = await _get_or_create_user_limits(session, user_id, today)
        daily_limit, _ = get_limits_for_user(is_premium)

        if limits.photos_used >= daily_limit:
            # Лимит уже исчерпан
            return False, limits.photos_used, daily_limit

        limits.photos_used += 1
        await session.commit()
        await session.refresh(limits)

        return True, limits.photos_used, daily_limit


async def get_user_today_analyses(user_id: int, today: date) -> int:
    """
    Получаем количество использованных анализов пользователем на сегодняшний день.
    """
    async with AsyncSessionLocal() as session:
        stmt = select(UserLimit).where(
            UserLimit.user_id == user_id,
            UserLimit.date == today
        )
        result = await session.execute(stmt)
        limits = result.scalar_one_or_none()

        if limits is None:
            return 0  # Если нет записи, возвращаем 0, а не None

        return limits.photos_used