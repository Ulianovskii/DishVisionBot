from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from app.bot.keyboards import premium_menu_kb
from app.bot.states import UserStates
from app.locales.ru.buttons import RussianButtons as B

router = Router()


@router.message(F.text == B.get("buy_premium"))
async def open_premium(message: Message, state: FSMContext):
    await state.set_state(UserStates.STANDARD)
    await message.answer(
        "💎 Премиум-аккаунт.\n"
        "Здесь позже будет интеграция с оплатой звёздами и статус тарифа.",
        reply_markup=premium_menu_kb(),
    )


@router.message(F.text == B.get("buy_week_confirm"))
async def buy_week_stub(message: Message):
    await message.answer(
        "💳 Покупка премиума на неделю (заглушка).\n"
        "Позже здесь будет Invoice/Stars."
    )


@router.message(F.text == B.get("buy_month_confirm"))
async def buy_month_stub(message: Message):
    await message.answer(
        "💳 Покупка премиума на месяц (заглушка).\n"
        "Позже здесь будет Invoice/Stars."
    )


@router.message(F.text == B.get("enter_promo"))
async def enter_promo_start(message: Message, state: FSMContext):
    await state.set_state(UserStates.PROMO)
    await message.answer(
        "🎟 Введите промокод одним сообщением.\n"
        "Пока это только заглушка без проверок."
    )


@router.message(UserStates.PROMO)
async def enter_promo_input(message: Message, state: FSMContext):
    await state.set_state(UserStates.STANDARD)
    await message.answer(
        f"🎟 Промокод принят (заглушка): {message.text}\n"
        "Позже здесь будет проверка в БД, активация и лимиты."
    )
