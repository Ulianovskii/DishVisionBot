# app/bot/handlers/analysis.py

from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from app.bot.keyboards import analysis_menu_kb, main_menu_kb
from app.bot.states import UserStates
from app.locales.ru.texts import RussianTexts as T
from app.locales.ru.buttons import RussianButtons as B

router = Router()


# 1. Любое фото — считаем стартом анализа
@router.message(F.photo)
async def on_photo_received(message: Message, state: FSMContext):
    """
    Пользователь прислал фото (из любого состояния).
    Сохраняем фото и переводим в режим уточнения комментария.
    """
    photo = message.photo[-1]  # самое большое фото
    file_id = photo.file_id

    await state.set_state(UserStates.PHOTO_COMMENT)
    await state.update_data(
        current_photo_file_id=file_id,
        current_comment="",
    )

    await message.answer(
        # пока без отдельного ключа в локалях, чтобы не ломать texts.py
        T.get("send_photo_for_analysis")
        + "\n\n"
        + "Можешь уточнить детали блюда текстом. "
          "Когда закончишь — нажми нужную кнопку ниже.",
        reply_markup=analysis_menu_kb(),
    )


# 2. Текст в режиме PHOTO_COMMENT — накапливаем комментарий
@router.message(UserStates.PHOTO_COMMENT, F.text)
async def on_comment_text(message: Message, state: FSMContext):
    """
    Пользователь дописывает комментарий к фото.
    Пока просто накапливаем текст в FSM, без ответа GPT.
    """
    data = await state.get_data()
    prev_comment = data.get("current_comment", "")

    new_comment = (prev_comment + "\n" + message.text).strip()

    await state.update_data(current_comment=new_comment)

    # Можно молчать, но давай лёгкий фидбек:
    await message.answer(
        "Записал комментарий 👍\n"
        "Когда будешь готов — нажми «Калорийность» или «Рецепт».",
        reply_markup=analysis_menu_kb(),
    )


# 3. Кнопка "Калорийность" — заглушка анализа питания
@router.message(UserStates.PHOTO_COMMENT, F.text == B.get("nutrition"))
async def on_nutrition_request(message: Message, state: FSMContext):
    """
    Потом здесь будем дергать GPT для анализа калорийности.
    Пока — заглушка.
    """
    data = await state.get_data()
    has_photo = "current_photo_file_id" in data

    if not has_photo:
        await message.answer(
            "Чтобы я смог оценить калорийность, сначала пришли фото блюда 📸",
            reply_markup=analysis_menu_kb(),
        )
        return

    await message.answer(
        "Здесь будет анализ калорийности и БЖУ.\n"
        "Пока функция в разработке 🔧",
        reply_markup=analysis_menu_kb(),
    )


# 4. Кнопка "Рецепт" — заглушка рецепта
@router.message(UserStates.PHOTO_COMMENT, F.text == B.get("recipe"))
async def on_recipe_request(message: Message, state: FSMContext):
    """
    Потом здесь будет GPT-рецепт по фото.
    Пока — заглушка.
    """
    data = await state.get_data()
    has_photo = "current_photo_file_id" in data

    if not has_photo:
        await message.answer(
            "Чтобы подсказать рецепт, сначала пришли фото блюда 📸",
            reply_markup=analysis_menu_kb(),
        )
        return

    await message.answer(
        "Здесь будет подробный рецепт и советы по приготовлению.\n"
        "Пока функция в разработке 🔧",
        reply_markup=analysis_menu_kb(),
    )


# 5. Кнопка "Новое фото"
@router.message(UserStates.PHOTO_COMMENT, F.text == B.get("new_photo"))
async def on_new_photo(message: Message, state: FSMContext):
    """
    Сброс текущего фото/комментария, просим прислать новое фото.
    """
    await state.update_data(current_photo_file_id=None, current_comment="")

    await message.answer(
        "Окей, давай начнём сначала.\nПришли новое фото блюда 📸",
        reply_markup=analysis_menu_kb(),
    )


# 6. Кнопка "Назад" — возвращаем в главное меню
@router.message(UserStates.PHOTO_COMMENT, F.text == B.get("back"))
async def on_back_to_main_from_photo(message: Message, state: FSMContext):
    """
    Кнопка 'Назад' из режима анализа — возвращаем пользователя в стандартный режим.
    """
    await state.set_state(UserStates.STANDARD)

    await message.answer(
        "Возвращаю в главное меню 🏠",
        reply_markup=main_menu_kb(),
    )
