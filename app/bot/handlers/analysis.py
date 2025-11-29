# app/bot/handlers/analysis.py

import logging

from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from openai import AsyncOpenAI

from app.bot.keyboards import analysis_menu_kb, main_menu_kb
from app.bot.states import UserStates
from app.config import settings
from app.locales.ru.texts import RussianTexts as T
from app.locales.ru.buttons import RussianButtons as B
from app.prompts.food_analysis import get_system_prompt

router = Router()
logger = logging.getLogger(__name__)

# Инициализируем клиент OpenAI один раз на модуль
openai_client = AsyncOpenAI(api_key=settings.openai_api_key)
GPT_MODEL = getattr(settings, "openai_model", "gpt-4o-mini")


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

    # Используем текст из локализации
    await message.answer(
        T.get("photo_received_options"),
        reply_markup=analysis_menu_kb(),
    )


# === КНОПКИ В РЕЖИМЕ PHOTO_COMMENT (СПЕРВА СПЕЦИФИЧНЫЕ) ===

# 2. Кнопка "Калорийность" — вызов GPT с промтом NUTRITION
@router.message(UserStates.PHOTO_COMMENT, F.text == B.get("nutrition"))
async def on_nutrition_request(message: Message, state: FSMContext):
    """
    Анализ калорийности и БЖУ с помощью GPT.
    Сейчас используем только текстовое описание (комментарий),
    фото телеграма в OpenAI пока не передаём (это отдельный этап).
    """
    data = await state.get_data()
    photo_id = data.get("current_photo_file_id")
    comment = data.get("current_comment") or ""

    if not photo_id:
        # Пользователь нажал кнопку, не отправив фото
        await message.answer(
            T.get("photo_first_then_text"),
            reply_markup=analysis_menu_kb(),
        )
        return

    system_prompt = get_system_prompt(
        user_description=comment,
        analysis_type="nutrition",
    )

    # Текст "анализирую" тоже берём из локализации
    await message.answer(T.get("analyzing_image"))

    try:
        response = await openai_client.chat.completions.create(
            model=GPT_MODEL,
            temperature=0.3,
            messages=[
                {
                    "role": "system",
                    "content": system_prompt,
                },
                {
                    "role": "user",
                    "content": (
                        "Проанализируй блюда на фото строго по инструкциям системного промта "
                        "и выведи результат в заданном формате."
                    ),
                },
            ],
        )

        content = response.choices[0].message.content or T.get("analysis_error")
        await message.answer(content, reply_markup=analysis_menu_kb())

    except Exception as e:
        logger.exception("Ошибка при вызове GPT для анализа калорийности: %s", e)
        await message.answer(
            T.get("analysis_error"),
            reply_markup=analysis_menu_kb(),
        )


# 3. Кнопка "Рецепт" — вызов GPT с промтом RECIPE
@router.message(UserStates.PHOTO_COMMENT, F.text == B.get("recipe"))
async def on_recipe_request(message: Message, state: FSMContext):
    """
    Получение рецепта по блюду с помощью GPT.
    Также опираемся на текстовый комментарий пользователя,
    фото в OpenAI пока не передаём.
    """
    data = await state.get_data()
    photo_id = data.get("current_photo_file_id")
    comment = data.get("current_comment") or ""

    if not photo_id:
        await message.answer(
            T.get("photo_first_then_text"),
            reply_markup=analysis_menu_kb(),
        )
        return

    system_prompt = get_system_prompt(
        user_description=comment,
        analysis_type="recipe",
    )

    await message.answer(T.get("analyzing_image"))

    try:
        response = await openai_client.chat.completions.create(
            model=GPT_MODEL,
            temperature=0.4,
            messages=[
                {
                    "role": "system",
                    "content": system_prompt,
                },
                {
                    "role": "user",
                    "content": (
                        "Дай подробные рецепты блюд на фото по инструкциям системного промта, "
                        "используя описание от пользователя."
                    ),
                },
            ],
        )

        content = response.choices[0].message.content or T.get("analysis_error")
        await message.answer(content, reply_markup=analysis_menu_kb())

    except Exception as e:
        logger.exception("Ошибка при вызове GPT для рецепта: %s", e)
        await message.answer(
            T.get("analysis_error"),
            reply_markup=analysis_menu_kb(),
        )


# 4. Кнопка "Новое фото"
@router.message(UserStates.PHOTO_COMMENT, F.text == B.get("new_photo"))
async def on_new_photo(message: Message, state: FSMContext):
    """
    Сброс текущего фото/комментария, просим прислать новое фото.
    """
    await state.update_data(current_photo_file_id=None, current_comment="")

    await message.answer(
        T.get("send_photo_for_analysis"),
        reply_markup=analysis_menu_kb(),
    )


# 5. Кнопка "Назад" — возвращаем в главное меню
@router.message(UserStates.PHOTO_COMMENT, F.text == B.get("back"))
async def on_back_to_main_from_photo(message: Message, state: FSMContext):
    """
    Кнопка 'Назад' из режима анализа — возвращаем пользователя в стандартный режим.
    Пока показываем текст приветствия бесплатного тарифа.
    """
    await state.set_state(UserStates.STANDARD)

    await message.answer(
        T.get("welcome_free"),
        reply_markup=main_menu_kb(),
    )


# 6. Текст в режиме PHOTO_COMMENT — накапливаем комментарий
@router.message(UserStates.PHOTO_COMMENT, F.text)
async def on_comment_text(message: Message, state: FSMContext):
    """
    Пользователь дописывает комментарий к фото.
    Накапливаем текст в FSM, без прямого обращения к GPT.
    """
    data = await state.get_data()
    prev_comment = data.get("current_comment", "")

    new_comment = (prev_comment + "\n" + message.text).strip()

    await state.update_data(current_comment=new_comment)

    await message.answer(
        T.get("refinement_hint"),
        reply_markup=analysis_menu_kb(),
    )
