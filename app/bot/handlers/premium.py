# app/bot/handlers/premium.py

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from sqlalchemy import select

from app.bot.states import UserStates
from app.bot.keyboards import premium_menu_kb, main_menu_kb
from app.locales.ru.buttons import RussianButtons as B
from app.locales.ru.texts import RussianTexts as T
from app.services.user_service import get_or_create_user
from app.db.base import AsyncSessionLocal
from app.db import models

router = Router(name="premium")


# ===== Вспомогательные функции времени =====

def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _normalize_to_utc(dt: datetime | None) -> datetime | None:
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


# ===== Открытие меню премиума (вызывается из main_menu) =====

async def open_premium_menu(message: Message, state: FSMContext) -> None:
    """
    Открываем экран покупки премиума / ввода промокода.

    Вызывается из main_menu.on_buy_premium, чтобы не плодить дублирующие хендлеры.
    """
    await state.set_state(UserStates.STANDARD)

    await message.answer(
        T.get("premium_info"),
        reply_markup=premium_menu_kb(),
    )


# ===== Ввод промокода =====

@router.message(F.text == B.get("enter_promo"))
async def on_enter_promo(message: Message, state: FSMContext) -> None:
    """
    Переход в режим ввода промокода.
    """
    await state.set_state(UserStates.PROMO)
    await message.answer(
        T.get("premium_promo_enter_prompt") or "Введите промокод. Если промокода нет — нажмите «🏠 Главная».",
        reply_markup=premium_menu_kb(),
    )


@router.message(UserStates.PROMO)
async def on_promo_input(message: Message, state: FSMContext) -> None:
    """
    Обработка введённого промокода.
    """
    text = (message.text or "").strip()

    # 1) Пользователь передумал и нажал "🏠 Главная" — выходим из режима промокода
    if text == B.get("back"):
        await state.set_state(UserStates.STANDARD)
        await message.answer(
            T.get("welcome_free"),
            reply_markup=main_menu_kb(),
        )
        return

    # 4) Остальное считаем промокодом
    raw_code = text
    if not raw_code:
        await message.answer(
            T.get("premium_promo_enter_prompt") or "Введите промокод:"
        )
        return

    code = raw_code.upper()

    telegram_id = message.from_user.id
    user = await get_or_create_user(telegram_id)

    success, reply_text = await _apply_promo_code(user_id=user.id, code=code)

    if not success:
        # При ошибке остаёмся в состоянии PROMO, чтобы можно было попробовать ещё раз
        await message.answer(
            reply_text,
            reply_markup=premium_menu_kb(),
        )
        return

    # Успешная активация: выходим из режима ввода
    await state.set_state(UserStates.STANDARD)

    # После успешного применения кода: показываем, что всё ок,
    # и отдаём клаву профиля с премиумом.
    from app.bot.handlers.profile import build_profile_keyboard  # локальный импорт, чтобы не ловить циклы

    await message.answer(
        reply_text,
        reply_markup=build_profile_keyboard(is_premium=True),
    )


# ===== LOW-LEVEL логика применения промокода =====

async def _apply_promo_code(user_id: int, code: str) -> tuple[bool, str]:
    """
    Реализация бизнес-логики промокодов.
    """
    now = _now_utc()

    async with AsyncSessionLocal() as session:
        # 1. Получаем пользователя
        user_stmt = select(models.User).where(models.User.id == user_id)
        user_res = await session.execute(user_stmt)
        user = user_res.scalar_one_or_none()

        if not user:
            # Теоретически не должно случаться
            return False, T.get("premium_promo_internal_error") or "Внутренняя ошибка при обработке промокода."

        # 2. Проверяем бан по промокодам
        ban_stmt = select(models.PromoBan).where(
            models.PromoBan.user_id == user.id,
            models.PromoBan.banned_until > now,
        )
        ban_res = await session.execute(ban_stmt)
        ban = ban_res.scalar_one_or_none()

        if ban:
            return False, T.get("premium_promo_banned") or "Вы временно не можете использовать промокоды."

        # 3. Ищем сам промокод
        promo_stmt = select(models.PromoCode).where(models.PromoCode.code == code)
        promo_res = await session.execute(promo_stmt)
        promo = promo_res.scalar_one_or_none()

        # Единый ответ, чтобы не подсвечивать, существует код или нет
        generic_invalid_msg = (
            T.get("premium_promo_invalid")
            or "Промокод недействителен, истёк или исчерпал лимит активаций."
        )

        if not promo:
            return False, generic_invalid_msg

        # 4. Проверка срока действия
        if promo.expires_at is not None:
            promo_expires = _normalize_to_utc(promo.expires_at)
            if promo_expires is not None and promo_expires < now:
                return False, generic_invalid_msg

        # 5. Проверка лимита активаций
        if promo.activations >= promo.max_activations:
            return False, generic_invalid_msg

        # 6. Проверка, что пользователь уже не активировал этот код
        act_stmt = select(models.PromoCodeActivation).where(
            models.PromoCodeActivation.promo_code_id == promo.id,
            models.PromoCodeActivation.user_id == user.id,
        )
        act_res = await session.execute(act_stmt)
        activation = act_res.scalar_one_or_none()

        if activation:
            msg = (
                T.get("premium_promo_already_used")
                or "Вы уже активировали этот промокод ранее."
            )
            return False, msg

        # 7. Применяем промокод → продлеваем премиум
        current_until = _normalize_to_utc(user.premium_until)

        # Премиум стакается
        base = now
        if current_until is not None and current_until > now:
            base = current_until

        new_until = base + timedelta(days=promo.days)

        user.is_premium = True
        user.premium_until = new_until

        # Увеличиваем счётчик активаций
        promo.activations = (promo.activations or 0) + 1

        # Создаём запись об активации
        new_activation = models.PromoCodeActivation(
            promo_code_id=promo.id,
            user_id=user.id,
        )
        session.add(new_activation)

        await session.commit()

    until_str = new_until.date().isoformat()
    success_msg = T.get(
        "premium_promo_success",
        days=promo.days,
        date=until_str,
    ) or f"Промокод активирован! Премиум продлён до {until_str}."

    return True, success_msg
