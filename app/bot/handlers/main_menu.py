# app/bot/handlers/main_menu.py

import logging

from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from app.bot.keyboards import (
    main_menu_kb,
    analysis_menu_kb,
    premium_menu_kb,
)
from app.bot.states import UserStates
from app.locales.ru.texts import RussianTexts as T
from app.locales.ru.buttons import RussianButtons as B

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
    Начало сценария анализа еды.

    Здесь мы больше НЕ проверяем лимиты.
    Лимиты проверяются при получении фото в analysis.on_photo_received().
    """
    await state.set_state(UserStates.PHOTO_COMMENT)
    await message.answer(
        T.get("send_photo_for_analysis"),
        reply_markup=analysis_menu_kb(),
    )


# Кнопка "Отчеты" — сейчас фактически не используется (отчёты отключены),
# но оставляем хендлер как заглушку.
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
