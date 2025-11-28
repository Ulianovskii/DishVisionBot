from aiogram import Router, F
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from app.services.user_service import get_or_create_user


from app.bot.keyboards import main_menu_kb
from app.bot.states import UserStates
from app.locales.ru.texts import RussianTexts as T
from app.locales.ru.buttons import RussianButtons as B

router = Router()


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    # создаём пользователя, если нужно
    if message.from_user:
        await get_or_create_user(message.from_user.id)

    await state.set_state(UserStates.STANDARD)
    await message.answer(
        T.get("send_photo_for_analysis"),
        reply_markup=main_menu_kb(),  # <-- здесь клавиатура точно прилетает
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

@router.message(UserStates.STANDARD)
async def standard_fallback(message: Message, state: FSMContext):
    """
    Любое текстовое сообщение в базовом состоянии,
    которое не попало в другие хендлеры, возвращает главное меню.
    """
    await state.set_state(UserStates.STANDARD)
    await message.answer(
        "🏠 Главное меню.",
        reply_markup=main_menu_kb(),
    )

