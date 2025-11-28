# app/bot/handlers/main_menu.py
from aiogram import Router, F
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from app.bot.keyboards import main_menu_kb, analysis_menu_kb
from app.bot.states import UserStates
from app.locales.ru.texts import RussianTexts as T
from app.locales.ru.buttons import RussianButtons as B
from app.services.user_service import get_or_create_user

router = Router()


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    """US1/US2: старт, создание пользователя, главная страница"""
    if message.from_user:
        await get_or_create_user(message.from_user.id)

    await state.set_state(UserStates.STANDARD)

    await message.answer(
        T.get("send_photo_for_analysis"),
        reply_markup=main_menu_kb(),
    )


@router.message(F.text == B.get("analyze_food"))
async def on_analyze_food(message: Message, state: FSMContext):
    """
    Пользователь нажал '📸 Анализировать еду'
    Пока без бизнес-логики: просто переводим в STATE_PHOTO_COMMENT
    и просим отправить фото.
    """
    await state.set_state(UserStates.PHOTO_COMMENT)

    await message.answer(
        T.get("send_photo_for_analysis"),
        reply_markup=analysis_menu_kb(),
    )


@router.message(F.text == B.get("help"))
async def on_help(message: Message, state: FSMContext):
    """
    US2: помощь.
    FSM остаётся в STANDARD (по ТЗ).
    """
    await state.set_state(UserStates.STANDARD)

    await message.answer(
        T.get("help_text"),
        reply_markup=main_menu_kb(),
    )


@router.message(F.text == B.get("profile"))
async def on_profile(message: Message, state: FSMContext):
    """
    US3: профиль (пока заглушка без данных из БД).
    """
    await state.set_state(UserStates.STANDARD)

    await message.answer(
        "👤 Профиль пока в разработке.\n"
        "Тут будет:\n"
        "• тип подписки\n"
        "• использованные лимиты за сегодня\n"
        "• план по калориям",
        reply_markup=main_menu_kb(),
    )


@router.message(F.text == B.get("reports"))
async def on_reports(message: Message, state: FSMContext):
    """
    US6: отчёты (заглушка).
    """
    await state.set_state(UserStates.STANDARD)

    await message.answer(
        "📊 Отчёты пока в разработке.\n"
        "Здесь появится:\n"
        "• отчет за день\n"
        "• за неделю\n"
        "• за месяц",
        reply_markup=main_menu_kb(),
    )


@router.message(F.text == B.get("buy_premium"))
async def on_buy_premium(message: Message, state: FSMContext):
    """
    US4: покупка премиума (заглушка экрана оплаты).
    """
    await state.set_state(UserStates.STANDARD)

    await message.answer(
        "💎 Экран оплаты премиума пока в разработке.\n"
        "План: Telegram Stars + промокоды.",
        reply_markup=main_menu_kb(),
    )
