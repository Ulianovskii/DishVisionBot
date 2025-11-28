from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from app.bot.keyboards import analysis_menu_kb
from app.bot.states import UserStates
from app.locales.ru.buttons import RussianButtons as B

router = Router()


@router.message(F.text == B.get("analyze_food"))
async def enter_analysis(message: Message, state: FSMContext):
    """
    Заходим в режим анализа еды.
    Пока без загрузки фото и GPT — только меню.
    """
    await state.set_state(UserStates.PHOTO_COMMENT)
    await message.answer(
        "📸 Режим анализа еды.\n"
        "Отправьте фото (пока заглушка) и выберите действие.",
        reply_markup=analysis_menu_kb(),
    )


@router.message(UserStates.PHOTO_COMMENT, F.text == B.get("nutrition"))
async def nutrition_stub(message: Message):
    await message.answer(
        "📊 Здесь будет анализ калорийности и БЖУ (заглушка)."
    )


@router.message(UserStates.PHOTO_COMMENT, F.text == B.get("recipe"))
async def recipe_stub(message: Message):
    await message.answer(
        "📖 Здесь будет генерация рецепта и рекомендаций (заглушка)."
    )


@router.message(UserStates.PHOTO_COMMENT, F.text == B.get("new_photo"))
async def new_photo_stub(message: Message):
    await message.answer(
        "📷 Здесь позже будем принимать новое фото и комментарии.\n"
        "Пока это просто заглушка."
    )
