from aiogram import Router, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from app.bot.keyboards import admin_menu_kb
from app.bot.states import UserStates
from app.locales.ru.buttons import RussianButtons as B

router = Router()


@router.message(Command("superadmin"))
async def enter_admin_menu(message: Message, state: FSMContext):
    # ⚠️ Пока без проверки ADMIN_USER_IDS — только навигация
    await state.set_state(UserStates.ADMIN)
    await message.answer(
        "🛠 Админ-меню (заглушка).\n"
        "Позже здесь будет проверка прав и статистика.",
        reply_markup=admin_menu_kb(),
    )


@router.message(UserStates.ADMIN, F.text == B.get("admin_statistics"))
async def admin_statistics_stub(message: Message):
    await message.answer("📈 Админ-статистика (заглушка).")


@router.message(UserStates.ADMIN, F.text == B.get("admin_manage_limits"))
async def admin_manage_limits_stub(message: Message, state: FSMContext):
    await state.set_state(UserStates.LIMIT_RESET)
    await message.answer(
        "🔁 Управление лимитами (заглушка).\n"
        "Позже здесь можно будет сбрасывать лимиты."
    )


@router.message(UserStates.ADMIN, F.text == B.get("admin_promo"))
async def admin_promo_stub(message: Message, state: FSMContext):
    await state.set_state(UserStates.PROMO_GENERATE)
    await message.answer(
        "🎟 Генерация промокодов (заглушка).\n"
        "Позже здесь будет выбор срока и генерация кодов."
    )


@router.message(UserStates.ADMIN, F.text == B.get("admin_exit"))
async def admin_exit(message: Message, state: FSMContext):
    await state.set_state(UserStates.STANDARD)
    await message.answer("⬅️ Выход из админ-меню. Возврат в главное меню.")
