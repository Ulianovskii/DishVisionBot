# app/bot/handlers/premium.py

from datetime import datetime, timedelta, timezone

from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from sqlalchemy import select

from app.bot.keyboards import premium_menu_kb, main_menu_kb
from app.bot.states import UserStates
from app.locales.ru.buttons import RussianButtons as B
from app.locales.ru.texts import RussianTexts as T
from app.db.base import AsyncSessionLocal
from app.db.models import User, PromoCode, PromoCodeActivation


router = Router()


def _now_utc() -> datetime:
    """
    Всегда возвращаем aware-datetime в UTC,
    чтобы не было конфликтов с таймзонными полями в БД.
    """
    return datetime.now(timezone.utc)


async def _get_or_create_user(session, telegram_id: int) -> User:
    """
    Локальный вариант get_or_create_user в рамках одной сессии,
    чтобы можно было сразу обновлять пользователя и коммитить.
    """
    stmt = select(User).where(User.telegram_id == telegram_id)
    result = await session.execute(stmt)
    user = result.scalar_one_or_none()

    if user:
        return user

    user = User(telegram_id=telegram_id)
    session.add(user)
    await session.flush()
    return user


def _normalize_to_utc(dt: datetime | None) -> datetime | None:
    """
    Приводим datetime к UTC-aware, если он есть.
    Если None — возвращаем None.
    """
    if dt is None:
        return None

    if dt.tzinfo is None:
        # считаем, что это UTC без таймзоны
        return dt.replace(tzinfo=timezone.utc)

    # переводим в UTC на всякий случай
    return dt.astimezone(timezone.utc)


def _calc_new_premium_until(current_until: datetime | None, days: int) -> datetime:
    """
    Продлеваем подписку:
    - если премиум ещё активен → прибавляем дни к текущей дате окончания;
    - если премиума нет или он истёк → считаем от текущего момента.
    Всё в UTC-aware.
    """
    now = _now_utc()
    current_until_utc = _normalize_to_utc(current_until)

    if current_until_utc and current_until_utc > now:
        base = current_until_utc
    else:
        base = now

    return base + timedelta(days=days)


@router.message(F.text == B.get("buy_premium"))
async def open_premium(message: Message, state: FSMContext):
    """
    Экран премиума. Оплата звёздами будет отдельным шагом.
    Сейчас премиум можно активировать только промокодом.
    """
    await state.set_state(UserStates.STANDARD)
    await message.answer(
        T.get("premium_info"),
        reply_markup=premium_menu_kb(),
    )


@router.message(F.text == B.get("buy_week_confirm"))
async def buy_week_stub(message: Message):
    await message.answer(
        "💳 Премиум за звёзды пока не подключён.\n"
        "Сейчас премиум можно активировать только промокодом."
    )


@router.message(F.text == B.get("buy_month_confirm"))
async def buy_month_stub(message: Message):
    await message.answer(
        "💳 Премиум за звёзды пока не подключён.\n"
        "Сейчас премиум можно активировать только промокодом."
    )


# ==== ПРОМОКОДЫ ДЛЯ ПОЛЬЗОВАТЕЛЕЙ ====


@router.message(F.text == B.get("enter_promo"))
async def enter_promo_start(message: Message, state: FSMContext):
    """
    Вход в режим ввода промокода.
    """
    await state.set_state(UserStates.PROMO)
    await message.answer("🎟 Введите промокод одним сообщением.")


@router.message(UserStates.PROMO)
async def enter_promo_input(message: Message, state: FSMContext):
    """
    Ввод промокода пользователем.

    Важно:
    - при НЕВЕРНОМ коде остаёмся в состоянии PROMO, чтобы можно было пробовать ещё раз;
    - при УСПЕХЕ выходим в STANDARD и показываем главное меню;
    - новый промокод всегда ДОБАВЛЯЕТ дни к уже существующей подписке, а не заменяет дату.
    """
    raw_code = (message.text or "").strip()
    if not raw_code:
        await message.answer("❌ Промокод не должен быть пустым.")
        return

    code = raw_code.upper()
    tg_id = message.from_user.id

    async with AsyncSessionLocal() as session:
        # 1. Находим или создаём пользователя
        user = await _get_or_create_user(session, tg_id)

        # 2. Ищем промокод
        stmt = select(PromoCode).where(PromoCode.code == code)
        result = await session.execute(stmt)
        promo: PromoCode | None = result.scalar_one_or_none()

        if promo is None:
            # Неверный код — остаёмся в PROMO
            await message.answer(T.get("promo_not_found"))
            return

        now = _now_utc()
        promo_expires_at = _normalize_to_utc(promo.expires_at)

        # 3. Проверяем срок действия
        if promo_expires_at and promo_expires_at < now:
            await message.answer(T.get("promo_expired"))
            return

        # 4. Проверяем лимит активаций
        if promo.activations >= promo.max_activations:
            await message.answer(T.get("promo_invalid"))
            return

        # 5. Проверяем, активировал ли уже этот пользователь этот промокод
        stmt = select(PromoCodeActivation).where(
            PromoCodeActivation.promo_code_id == promo.id,
            PromoCodeActivation.user_id == user.id,
        )
        result = await session.execute(stmt)
        already_used = result.scalar_one_or_none()

        if already_used:
            await message.answer(T.get("promo_already_used"))
            return

        # 6. Применяем промокод: продлеваем премиум на promo.days
        new_until = _calc_new_premium_until(user.premium_until, promo.days)
        user.is_premium = True
        user.premium_until = new_until

        # 7. Фиксируем активацию
        promo.activations += 1
        activation = PromoCodeActivation(
            promo_code_id=promo.id,
            user_id=user.id,
        )
        session.add(activation)

        await session.commit()

    # 8. Успешная активация — выходим в стандартное состояние + главное меню
    await state.set_state(UserStates.STANDARD)

    # Форматируем дату для пользователя — YYYY-MM-DD
    until_str = new_until.date().isoformat()

    await message.answer(
        T.get("promo_success", until=until_str),
        reply_markup=main_menu_kb(),
    )
