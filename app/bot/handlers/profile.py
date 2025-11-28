from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from app.bot.keyboards import profile_menu_kb
from app.bot.states import UserStates
from app.locales.ru.buttons import RussianButtons as B
from app.locales.ru.texts import RussianTexts as T

router = Router()


@router.message(F.text == B.get("profile"))
async def open_profile(message: Message, state: FSMContext):
    await state.set_state(UserStates.STANDARD)
    await message.answer(
        "👤 Профиль пользователя.\n"
        "Здесь позже будет информация о тарифе, лимитах и план калорий.",
        reply_markup=profile_menu_kb(),
    )


@router.message(F.text == B.get("set_calorie_goal"))
async def set_calorie_goal_start(message: Message, state: FSMContext):
    await state.set_state(UserStates.CALORIES_PLAN)
    await message.answer(T.get("calories_plan_prompt"))


@router.message(UserStates.CALORIES_PLAN)
async def set_calorie_goal_input(message: Message, state: FSMContext):
    # Пока не валидируем ввод, просто заглушка
    await state.set_state(UserStates.STANDARD)
    await message.answer(
        f"🎯 План калорий сохранён (заглушка): {message.text}\n"
        "Позже здесь будет валидация и запись в БД."
    )
