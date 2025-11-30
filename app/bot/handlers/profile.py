# app/bot/handlers/profile.py

from datetime import datetime, date, timezone

from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton

from app.bot.states import UserStates
from app.locales.ru.buttons import RussianButtons as B
from app.locales.ru.texts import RussianTexts as T
from app.services.user_service import get_or_create_user
from app.services.limit_service import get_limits_for_user, get_user_today_analyses

router = Router(name="profile")


def _now_utc() -> datetime:
    """Единая точка получения текущего времени (UTC-aware)."""
    return datetime.now(timezone.utc)


def _normalize_to_utc(dt: datetime | None) -> datetime | None:
    """Приводим datetime к UTC-aware, чтобы не ловить naive/aware ошибки."""
    if dt is None:
        return None

    if dt.tzinfo is None:
        # считаем, что это уже UTC, просто добавляем таймзону
        return dt.replace(tzinfo=timezone.utc)

    return dt.astimezone(timezone.utc)


def _is_effective_premium(user) -> bool:
    """
    Реально ли у пользователя активен премиум сейчас:
    - user.is_premium == True
    - premium_until в будущем (UTC) ИЛИ premium_until == None (бессрочный премиум)
    """
    if not getattr(user, "is_premium", False):
        return False

    premium_until = _normalize_to_utc(getattr(user, "premium_until", None))

    # None трактуем как "бессрочный премиум"
    if premium_until is None:
        return True

    now = _now_utc()
    return premium_until > now


def build_profile_keyboard(is_premium: bool = False) -> ReplyKeyboardMarkup:
    """
    Клавиатура профиля:
    - Анализировать еду
    - Помощь
    - Профиль
    - (опционально) Купить премиум
    """
    rows = [
        [
            KeyboardButton(text=B.get("analyze_food")),
            KeyboardButton(text=B.get("help")),
        ],
        [
            KeyboardButton(text=B.get("profile")),
        ],
    ]

    if not is_premium:
        rows.append([KeyboardButton(text=B.get("buy_premium"))])

    return ReplyKeyboardMarkup(
        keyboard=rows,
        resize_keyboard=True,
    )


@router.message(F.text == B.get("profile"))
async def on_profile_open(message: Message, state: FSMContext):
    """
    Профиль пользователя:
    - статус подписки (бесплатный / премиум);
    - доступные анализы на сегодня (учитывая дневной лимит и купленные);
    - разбор по дневному лимиту и купленным анализам.
    """
    await state.set_state(UserStates.STANDARD)

    telegram_id = message.from_user.id
    user = await get_or_create_user(telegram_id)

    is_premium = _is_effective_premium(user)
    daily_limit, _ = get_limits_for_user(is_premium=is_premium)

    today = date.today()
    used_today = await get_user_today_analyses(user.id, today)
    if used_today is None:
        used_today = 0

    remaining_daily = max(daily_limit - used_today, 0)

    # Купленные дополнительные анализы (могут быть None)
    paid_balance = getattr(user, "paid_photos_balance", 0) or 0

    # Итог: сколько анализов можно сделать прямо сейчас
    total_available = remaining_daily + paid_balance

    lines: list[str] = []

    # Статус подписки
    if is_premium:
        lines.append(T.get("profile_subscription_premium"))
    else:
        lines.append(T.get("profile_subscription_free"))

    # Итог по доступным анализам
    lines.append(
        T.get("profile_total_today", total=total_available)
    )

    # Разбор по дневному лимиту
    lines.append("")
    lines.append(
        T.get(
            "profile_analyses_today",
            used=used_today,
            limit=daily_limit,
            remaining=remaining_daily,
        )
    )

    # Купленные анализы
    lines.append("")
    lines.append(
        T.get("profile_paid_analyses", paid=paid_balance)
    )

    await message.answer(
        "\n".join(lines),
        reply_markup=build_profile_keyboard(is_premium=is_premium),
    )


@router.message(F.text == B.get("calorie_plan"))
async def on_calorie_plan_start(message: Message, state: FSMContext):
    """
    Вход в режим ввода плана калорий.
    Сейчас эта функция не подсвечивается в интерфейсе,
    но хендлер оставляем на будущее.
    """
    await state.set_state(UserStates.CALORIES_PLAN)

    await message.answer(
        T.get("calories_plan_prompt")
    )


@router.message(UserStates.CALORIES_PLAN)
async def on_calorie_plan_input(message: Message, state: FSMContext):
    """
    Ввод плана калорий.
    Сейчас: только валидация и тексты, без сохранения в БД.
    """
    text = (message.text or "").strip()

    try:
        value = int(text)
    except ValueError:
        await message.answer(T.get("calories_plan_invalid"))
        return

    if value < 0 or value > 10000:
        await message.answer(T.get("calories_plan_invalid"))
        return

    if value == 0:
        await message.answer(T.get("calories_plan_reset"))
    else:
        await message.answer(T.get("calories_plan_saved", calories=value))

    await state.set_state(UserStates.STANDARD)

    telegram_id = message.from_user.id
    user = await get_or_create_user(telegram_id)
    is_premium = _is_effective_premium(user)

    await message.answer(
        T.get("profile_updated"),
        reply_markup=build_profile_keyboard(is_premium=is_premium),
    )
