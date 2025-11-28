from aiogram import Router, F
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from app.bot.keyboards import main_menu_kb
from app.bot.states import UserStates
from app.locales.ru.texts import RussianTexts as T
from app.locales.ru.buttons import RussianButtons as B

router = Router()


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    await state.set_state(UserStates.STANDARD)
    await message.answer(
        T.get("send_photo_for_analysis"),
        reply_markup=main_menu_kb(),
    )


@router.message(Command("help"))
async def cmd_help(message: Message):
    await message.answer(T.get("help_text"))


@router.message(F.text == B.get("back"))
async def go_back_to_main(message: Message, state: FSMContext):
    """
    Кнопка 'Главная' из любого состояния возвращает в главное меню.
    """
    await state.set_state(UserStates.STANDARD)
    await message.answer(
        "🏠 Главное меню (логика пока в разработке).",
        reply_markup=main_menu_kb(),
    )
