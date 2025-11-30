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

router = Router()


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
    - premium_until в будущем (UTC)
    """
    if not getattr(user, "is_premium", False):
        return False

    premium_until = _normalize_to_utc(getattr(user, "premium_until", None))
    if not premium_until:
        return False

    now = _now_utc()
    return premium_until > now


def build_profile_keyboard(is_premium: bool = False) -> ReplyKeyboardMarkup:
    """
    Клавиатура профиля:
    - Анализировать еду
    - Помощь
    - Отчёты
    - План калорий
    - Купить премиум (если тариф бесплатный)
    """
    rows = [
        [
            KeyboardButton(text=B.get("analyze_food")),
            KeyboardButton(text=B.get("help")),
        ],
        [
            KeyboardButton(text=B.get("reports")),
            KeyboardButton(text=B.get("calorie_plan")),
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
    - дата окончания премиума (если есть);
    - использованные лимиты за сегодня.
    План калорий пока без привязки к БД (будет позже).
    """
    await state.set_state(UserStates.STANDARD)

    # Берём пользователя из БД (через сервис, не завязываемся на middleware)
    telegram_id = message.from_user.id
    user = await get_or_create_user(telegram_id)

    # Реально ли премиум активен сейчас
    is_premium = _is_effective_premium(user)

    # Лимиты по тарифу
    daily_limit, _ = get_limits_for_user(is_premium=is_premium)

    # Сколько анализов уже использовано сегодня
    today = date.today()
    used_today = await get_user_today_analyses(user.id, today)
    if used_today is None:
        used_today = 0

    remaining = max(daily_limit - used_today, 0)

    # Собираем текст профиля
    lines: list[str] = []

    if is_premium:
        lines.append(T.get("profile_subscription_premium"))
    else:
        lines.append(T.get("profile_subscription_free"))

    premium_until_utc = _normalize_to_utc(getattr(user, "premium_until", None))
    if premium_until_utc and is_premium:
        # Показываем дату в формате YYYY-MM-DD
        until_str = premium_until_utc.date().isoformat()
        lines.append(T.get("profile_premium_until", date=until_str))

    lines.append(
        T.get("profile_used_today", used=used_today, limit=daily_limit)
    )
    lines.append(
        T.get("profile_remaining", remaining=remaining)
    )

    # Блок про план калорий оставляем простым, без БД (реализуем позже)
    lines.append("")
    lines.append("🎯 План по калориям: не задан.")
    lines.append("Нажмите «План калорий», чтобы задать его (логика будет добавлена позже).")

    await message.answer(
        "\n".join(lines),
        reply_markup=build_profile_keyboard(is_premium=is_premium),
    )


@router.message(F.text == B.get("calorie_plan"))
async def on_calorie_plan_start(message: Message, state: FSMContext):
    """
    Вход в режим ввода плана калорий.
    Пока просто валидируем число и показываем сообщения — связь с БД будет позже.
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
        # TODO: сбросить план в БД
        await message.answer(T.get("calories_plan_reset"))
    else:
        # TODO: сохранить план в БД
        await message.answer(T.get("calories_plan_saved", calories=value))

    await state.set_state(UserStates.STANDARD)

    # Обновлённый профиль после изменения плана (пока без реального чтения плана)
    telegram_id = message.from_user.id
    user = await get_or_create_user(telegram_id)
    is_premium = _is_effective_premium(user)

    await message.answer(
        "Профиль обновлён.",
        reply_markup=build_profile_keyboard(is_premium=is_premium),
    )
