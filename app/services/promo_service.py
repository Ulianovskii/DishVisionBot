# app/services/promo_service.py

import secrets
from datetime import datetime, timedelta

from sqlalchemy import select, func
from sqlalchemy.exc import IntegrityError

from app.db.base import AsyncSessionLocal
from app.db.models import (
    PromoCode,
    PromoCodeActivation,
    PromoBan,
    User,
)
from app.config_limits import (
    PROMO_MAX_ATTEMPTS_BEFORE_BAN,
    PROMO_BAN_MINUTES_FIRST,
    PROMO_BAN_MINUTES_SECOND,
    PROMO_BAN_MINUTES_THIRD,
)


# -----------------------------------------------------------
# Генерация промокодов (админ)
# -----------------------------------------------------------

async def generate_promo_codes(count: int, days: int, created_by: int, expires_at=None) -> list[str]:
    """
    Генерирует count промокодов, каждый на days дней премиума.
    expires_at можно передать руками, иначе не задаём.
    """
    codes = []

    async with AsyncSessionLocal() as session:
        for _ in range(count):
            code = secrets.token_hex(4).upper()   # 8 символов вида A1B2C3D4
            promo = PromoCode(
                code=code,
                days=days,
                max_activations=1,
                activations=0,
                expires_at=expires_at,
                created_by=created_by,
            )
            session.add(promo)
            codes.append(code)

        await session.commit()

    return codes


# -----------------------------------------------------------
# Получение промокода из БД
# -----------------------------------------------------------

async def get_code(code: str) -> PromoCode | None:
    async with AsyncSessionLocal() as session:
        stmt = select(PromoCode).where(func.lower(PromoCode.code) == code.lower())
        result = await session.execute(stmt)
        return result.scalar_one_or_none()


# -----------------------------------------------------------
# Анти-спам: бан за неверные промокоды
# -----------------------------------------------------------

async def register_failed_attempt(user_id: int):
    """
    Записываем неверный ввод промокода.
    Если достигнут лимит — выдаём бан.
    """
    async with AsyncSessionLocal() as session:
        # Считаем попытки за последние 24 часа
        since = datetime.utcnow() - timedelta(hours=24)
        stmt = (
            select(func.count())
            .select_from(PromoCodeActivation)
            .where(
                PromoCodeActivation.user_id == user_id,
                PromoCodeActivation.activated_at >= since,
                PromoCodeActivation.promo_code_id == None,  # type: ignore
            )
        )
        result = await session.execute(stmt)
        failures = result.scalar() or 0

        failures += 1

        # Создаём запись о неуспешной попытке
        session.add(
            PromoCodeActivation(
                user_id=user_id,
                promo_code_id=None,  # type: ignore
            )
        )

        # Проверяем пороги бана
        if failures >= PROMO_MAX_ATTEMPTS_BEFORE_BAN:
            # Считаем количество предыдущих банов
            bans_stmt = select(func.count()).select_from(PromoBan).where(PromoBan.user_id == user_id)
            bans_res = await session.execute(bans_stmt)
            ban_count = bans_res.scalar() or 0

            if ban_count == 0:
                minutes = PROMO_BAN_MINUTES_FIRST
            elif ban_count == 1:
                minutes = PROMO_BAN_MINUTES_SECOND
            else:
                minutes = PROMO_BAN_MINUTES_THIRD

            banned_until = datetime.utcnow() + timedelta(minutes=minutes)

            ban = PromoBan(
                user_id=user_id,
                banned_until=banned_until,
                reason="Too many invalid promo attempts"
            )
            session.add(ban)

        await session.commit()


async def check_ban(user_id: int) -> datetime | None:
    """
    Проверяет, забанен ли пользователь по промокодам.
    Возвращает datetime разбана или None.
    """
    async with AsyncSessionLocal() as session:
        now = datetime.utcnow()
        stmt = select(PromoBan).where(
            PromoBan.user_id == user_id,
            PromoBan.banned_until > now
        )
        res = await session.execute(stmt)
        ban = res.scalar_one_or_none()

        if ban:
            return ban.banned_until

        return None


# -----------------------------------------------------------
# Активация промокода
# -----------------------------------------------------------

async def activate_code(user_id: int, code: str):
    """
    Пытается активировать промокод.
    Возвращает: (status: str, extra: dict)
    """

    async with AsyncSessionLocal() as session:
        # Проверяем бан
        ban_until = await check_ban(user_id)
        if ban_until:
            return "banned", {"until": ban_until}

        promo = await get_code(code)
        if not promo:
            await register_failed_attempt(user_id)
            return "not_found", {}

        # Проверка срока
        if promo.expires_at and promo.expires_at < datetime.utcnow():
            await register_failed_attempt(user_id)
            return "expired", {}

        # Проверка лимита активаций
        if promo.activations >= promo.max_activations:
            await register_failed_attempt(user_id)
            return "already_used", {}

        # Проверка: активировал ли раньше этот промо
        stmt = select(PromoCodeActivation).where(
            PromoCodeActivation.promo_code_id == promo.id,
            PromoCodeActivation.user_id == user_id
        )
        rs = await session.execute(stmt)
        existing = rs.scalar_one_or_none()
        if existing:
            await register_failed_attempt(user_id)
            return "already_used", {}

        # Всё ок — активируем
        # 1) продлеваем премиум
        user_stmt = select(User).where(User.id == user_id)
        ur = await session.execute(user_stmt)
        user = ur.scalar_one()

        now = datetime.utcnow()
        base = user.premium_until if (user.premium_until and user.premium_until > now) else now

        new_until = base + timedelta(days=promo.days)
        user.is_premium = True
        user.premium_until = new_until

        # 2) записываем активацию
        activation = PromoCodeActivation(
            promo_code_id=promo.id,
            user_id=user_id,
        )
        session.add(activation)

        # 3) увеличиваем счётчик активаций
        promo.activations += 1

        await session.commit()

        return "ok", {"until": new_until}
