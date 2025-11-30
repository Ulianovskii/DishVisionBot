# app/bot/handlers/main_menu.py

import logging
from datetime import date, datetime, timezone

from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from app.bot.keyboards import main_menu_kb, analysis_menu_kb, premium_menu_kb
from app.bot.states import UserStates
from app.locales.ru.texts import RussianTexts as T
from app.locales.ru.buttons import RussianButtons as B
from app.services.user_service import get_or_create_user
from app.config_limits import PRICE_PER_ANALYSIS
from app.services.limit_service import get_limits_for_user, get_user_today_analyses



router = Router()
logger = logging.getLogger(__name__)


def _is_effective_premium(user) -> bool:
    """
    Пользователь считается премиумным, если:
    - is_premium = True
    - premium_until не истёк (или нет даты → бесконечный премиум)
    """
    if not getattr(user, "is_premium", False):
        return False

    premium_until = getattr(user, "premium_until", None)

    # aware datetime (UTC)
    now = datetime.now(timezone.utc)

    if premium_until is None:
        return True  # бессрочный премиум

    return premium_until > now


# /start — вход в бота
@router.message(F.text == "/start")
async def cmd_start(message: Message, state: FSMContext):
    await state.set_state(UserStates.STANDARD)
    # Пока приветствие одинаковое по лимитам, поэтому используем общий текст
    await message.answer(
        T.get("welcome_free"),
        reply_markup=main_menu_kb(),
    )


# Кнопка "📸 Анализировать еду"
@router.message(UserStates.STANDARD, F.text == B.get("analyze_food"))
async def on_analyze_food(message: Message, state: FSMContext):
    """
    Начинаем процесс анализа еды. Проверка на лимиты с учётом тарифа.
    """
    telegram_id = message.from_user.id
    user = await get_or_create_user(telegram_id)

    is_premium = _is_effective_premium(user)
    daily_limit, _ = get_limits_for_user(is_premium)

    today = date.today()
    used_analyses = await get_user_today_analyses(user.id, today)
    if used_analyses is None:
        used_analyses = 0

    if used_analyses >= daily_limit:
        await message.answer(
            T.get("daily_limit_exceeded").format(limit=daily_limit)
            + "\n"
            + T.get("buy_additional_analyses").format(
                number_of_analyses=PRICE_PER_ANALYSIS["number_of_analyses"],
                price=PRICE_PER_ANALYSIS["price"],
            ),
            reply_markup=main_menu_kb(),
        )
        return

    await state.set_state(UserStates.PHOTO_COMMENT)
    await message.answer(
        T.get("send_photo_for_analysis"),
        reply_markup=analysis_menu_kb(),
    )


# Кнопка "Отчеты"
@router.message(UserStates.STANDARD, F.text == B.get("reports"))
async def on_reports(message: Message, state: FSMContext):
    await message.answer(
        T.get("reports_placeholder"),
        reply_markup=main_menu_kb(),
    )


# Кнопка "Помощь"
@router.message(UserStates.STANDARD, F.text == B.get("help"))
async def on_help(message: Message, state: FSMContext):
    await message.answer(
        T.get("help_text"),
        reply_markup=main_menu_kb(),
    )


# Кнопка "Профиль"
@router.message(UserStates.STANDARD, F.text == B.get("profile"))
async def on_profile(message: Message, state: FSMContext):
    # Переход в профиль обрабатывается в profile.py, здесь просто заглушка на случай коллизий
    await message.answer(
        T.get("feature_development"),
        reply_markup=main_menu_kb(),
    )


# Кнопка "Купить премиум"
@router.message(UserStates.STANDARD, F.text == B.get("buy_premium"))
async def on_buy_premium(message: Message, state: FSMContext):
    """
    Открываем экран покупки премиума:
    - недельная подписка
    - месячная подписка
    - ввод промокода
    """
    await state.set_state(UserStates.STANDARD)

    await message.answer(
        T.get("premium_info"),
        reply_markup=premium_menu_kb(),
    )


# Универсальная кнопка "Главная"
@router.message(F.text == B.get("back"))
async def on_back_to_main(message: Message, state: FSMContext):
    await state.set_state(UserStates.STANDARD)
    await message.answer(
        T.get("welcome_free"),
        reply_markup=main_menu_kb(),
    )


# Fallback: любой текст в STANDARD
@router.message(UserStates.STANDARD, F.text)
async def on_unknown_in_main(message: Message, state: FSMContext):
    await message.answer(
        T.get("help_text"),
        reply_markup=main_menu_kb(),
    )
