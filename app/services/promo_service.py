# app/services/promo_service.py

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import List, Optional, Tuple

from sqlalchemy import select

from app.db.base import AsyncSessionLocal
from app.db import models


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


# =====================================================
#               ГЕНЕРАЦИЯ ПРОМОКОДОВ (АДМИНКА)
# =====================================================

async def generate_promo_codes(
    count: int,
    days: int,
    created_by: Optional[int] = None,
    expires_at: Optional[datetime] = None,
    max_activations: int = 1,
) -> List[str]:
    """
    Генерация `count` промокодов на `days` дней премиума.

    max_activations:
      - по умолчанию 1: один код = одна активация
      - можно задать больше, если нужно многоразовое использование
    """
    codes: List[str] = []

    async with AsyncSessionLocal() as session:
        for _ in range(count):
            code = _generate_code()

            promo = models.PromoCode(
                code=code,
                days=days,
                max_activations=max_activations,
                activations=0,
                expires_at=expires_at,
                created_by=created_by,
            )
            session.add(promo)
            codes.append(code)

        await session.commit()

    return codes


def _generate_code() -> str:
    """
    Короткий человекочитаемый код, например: 065E89D9
    """
    import secrets

    return secrets.token_hex(4).upper()


# =====================================================
#             АКТИВАЦИЯ ПРОМОКОДА ПОЛЬЗОВАТЕЛЕМ
# =====================================================

async def redeem_promo_code(
    code: str,
    telegram_id: int,
) -> Tuple[bool, str, Optional[int]]:
    """
    Активация промокода пользователем.

    Возвращает:
      - success: bool
      - reason: str:
          "ok"        — успешно,
          "not_found" — кода нет,
          "used"      — промокод исчерпан или уже использован этим пользователем,
          "expired"   — истёк срок действия,
          "internal"  — внутренняя ошибка.
      - days: Optional[int] — сколько дней премиума добавлено (если success=True)
    """
    code = (code or "").strip().upper()
    if not code:
        return False, "not_found", None

    async with AsyncSessionLocal() as session:
        try:
            # 1. Ищем промокод
            stmt = select(models.PromoCode).where(models.PromoCode.code == code)
            res = await session.execute(stmt)
            promo: models.PromoCode | None = res.scalar_one_or_none()

            if not promo:
                return False, "not_found", None

            now = _now_utc()

            # 2. Проверяем истечение срока
            if promo.expires_at is not None:
                exp = promo.expires_at
                if exp.tzinfo is None:
                    exp = exp.replace(tzinfo=timezone.utc)
                else:
                    exp = exp.astimezone(timezone.utc)

                if exp < now:
                    return False, "expired", None

            # 3. Проверяем, не исчерпаны ли активации
            current_activations = promo.activations or 0
            if current_activations >= promo.max_activations:
                return False, "used", None

            # 4. Находим / создаём пользователя по telegram_id
            stmt_user = select(models.User).where(
                models.User.telegram_id == telegram_id
            )
            res_user = await session.execute(stmt_user)
            user: models.User | None = res_user.scalar_one_or_none()

            if not user:
                user = models.User(
                    telegram_id=telegram_id,
                    is_premium=False,
                    premium_until=None,
                )
                session.add(user)
                await session.flush()  # чтобы получить user.id

            # 5. Проверяем, не активировал ли этот юзер уже этот промокод
            stmt_act = select(models.PromoCodeActivation).where(
                models.PromoCodeActivation.promo_code_id == promo.id,
                models.PromoCodeActivation.user_id == user.id,
            )
            res_act = await session.execute(stmt_act)
            activation = res_act.scalar_one_or_none()

            if activation is not None:
                # этот пользователь уже пользовался этим кодом
                return False, "used", None

            # 6. Продление / включение премиума
            now_utc = now
            base_from = now_utc

            if user.premium_until is not None:
                pu = user.premium_until
                if pu.tzinfo is None:
                    pu = pu.replace(tzinfo=timezone.utc)
                else:
                    pu = pu.astimezone(timezone.utc)

                # если премиум ещё действует — продлеваем от конца,
                # если уже истёк — от текущего момента
                if pu > now_utc:
                    base_from = pu

            user.is_premium = True
            user.premium_until = base_from + timedelta(days=promo.days)

            # 7. Записываем активацию и увеличиваем счётчик
            new_activation = models.PromoCodeActivation(
                promo_code_id=promo.id,
                user_id=user.id,
            )
            session.add(new_activation)

            promo.activations = current_activations + 1

            await session.commit()
            return True, "ok", promo.days

        except Exception:
            await session.rollback()
            return False, "internal", None
