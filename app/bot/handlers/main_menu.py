# app/bot/handlers/main_menu.py

import logging

from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from app.bot.keyboards import main_menu_kb, analysis_menu_kb
from app.bot.states import UserStates
from app.locales.ru.texts import RussianTexts as T
from app.locales.ru.buttons import RussianButtons as B
from app.services.limit_service import get_limits_for_user  # Убираем асинхронность здесь
from app.services.user_service import get_or_create_user
from app.config_limits import PRICE_PER_ANALYSIS  # Импортируем цену за анализ

router = Router()
logger = logging.getLogger(__name__)

# /start — вход в бота
@router.message(F.text == "/start")
async def cmd_start(message: Message, state: FSMContext):
    await state.set_state(UserStates.STANDARD)
    await message.answer(
        T.get("welcome_free"),
        reply_markup=main_menu_kb(),
    )


# Кнопка "📸 Анализировать еду"
@router.message(UserStates.STANDARD, F.text == B.get("analyze_food"))
async def on_analyze_food(message: Message, state: FSMContext):
    """
    Начинаем процесс анализа еды. Проверка на лимиты.
    """
    # Получаем пользователя и проверяем его лимиты
    telegram_id = message.from_user.id
    user = await get_or_create_user(telegram_id)
    is_premium = False  # Замените на реальную логику, если требуется проверка премиум

    daily_limit, _ = get_limits_for_user(is_premium)

    # Получаем сегодня анализы из БД
    data = await state.get_data()
    today = date.today()

    # Получаем количество использованных анализов на сегодня
    used_analyses = await get_user_today_analyses(user.id, today)

    if used_analyses >= daily_limit:
        # Лимит исчерпан
        await message.answer(
            T.get("daily_limit_exceeded").format(limit=daily_limit) + 
            f"\n{T.get('buy_additional_analyses').format(number_of_analyses=PRICE_PER_ANALYSIS['number_of_analyses'], price=PRICE_PER_ANALYSIS['price'])}",
            reply_markup=main_menu_kb()
        )
        return

    # Продолжаем работу, если лимит не исчерпан
    await state.set_state(UserStates.PHOTO_COMMENT)
    await message.answer(
        T.get("send_photo_for_analysis"),
        reply_markup=analysis_menu_kb()
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


# Кнопка "Профиль" (заглушка)
@router.message(UserStates.STANDARD, F.text == B.get("profile"))
async def on_profile(message: Message, state: FSMContext):
    await message.answer(
        T.get("feature_development"),
        reply_markup=main_menu_kb(),
    )


# Кнопка "Купить премиум" (заглушка)
@router.message(UserStates.STANDARD, F.text == B.get("buy_premium"))
async def on_buy_premium(message: Message, state: FSMContext):
    await message.answer(
        T.get("feature_development"),
        reply_markup=main_menu_kb(),
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
