import logging

from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from app.bot.keyboards import analysis_menu_kb, main_menu_kb
from app.bot.states import UserStates
from app.locales.ru.texts import RussianTexts as T
from app.locales.ru.buttons import RussianButtons as B
from app.services.gpt_client import (
    analyze_nutrition_by_text,
    analyze_recipe_by_text,
)

router = Router()
logger = logging.getLogger(__name__)

# Временный базовый лимит уточнений на одно фото.
# Позже сюда подставим значения из тарифов (free / premium).
MAX_REFINEMENTS_PER_PHOTO = 5


# 1. Любое фото — старт сценария анализа
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
        last_analysis_type=None,   # "nutrition" / "recipe" после первого анализа
        refinements_used=0,        # счётчик уточнений на это фото
    )

    await message.answer(
        T.get("photo_received_options"),
        reply_markup=analysis_menu_kb(),
    )


# === КНОПКИ В РЕЖИМЕ PHOTO_COMMENT ===

# 2. Кнопка "Калорийность"
@router.message(UserStates.PHOTO_COMMENT, F.text == B.get("nutrition"))
async def on_nutrition_request(message: Message, state: FSMContext):
    """
    Анализ калорийности и БЖУ с помощью GPT.
    Используем накопленный текстовый комментарий пользователя.
    """
    data = await state.get_data()
    photo_id = data.get("current_photo_file_id")
    comment = data.get("current_comment") or ""

    if not photo_id:
        # На всякий случай защита: нажали кнопку без фото
        await message.answer(
            T.get("photo_first_then_text"),
            reply_markup=analysis_menu_kb(),
        )
        return

    await message.answer(T.get("analyzing_image"))

    try:
        content = await analyze_nutrition_by_text(comment)
        content = content or T.get("analysis_error")

        # Запоминаем, что последний анализ был по калорийности
        await state.update_data(last_analysis_type="nutrition")

        await message.answer(content, reply_markup=analysis_menu_kb())

    except Exception as e:
        logger.exception("Ошибка при вызове GPT для анализа калорийности: %s", e)
        await message.answer(
            T.get("analysis_error"),
            reply_markup=analysis_menu_kb(),
        )


# 3. Кнопка "Рецепт"
@router.message(UserStates.PHOTO_COMMENT, F.text == B.get("recipe"))
async def on_recipe_request(message: Message, state: FSMContext):
    """
    Получение рецепта по блюду с помощью GPT.
    Используем накопленный текстовый комментарий пользователя.
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

    await message.answer(T.get("analyzing_image"))

    try:
        content = await analyze_recipe_by_text(comment)
        content = content or T.get("analysis_error")

        # Запоминаем, что последний анализ был по рецепту
        await state.update_data(last_analysis_type="recipe")

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
    await state.update_data(
        current_photo_file_id=None,
        current_comment="",
        last_analysis_type=None,
        refinements_used=0,
    )

    await message.answer(
        T.get("send_photo_for_analysis"),
        reply_markup=analysis_menu_kb(),
    )


# 5. Кнопка "Назад" — возвращаем в главное меню
@router.message(UserStates.PHOTO_COMMENT, F.text == B.get("back"))
async def on_back_to_main_from_photo(message: Message, state: FSMContext):
    """
    Кнопка 'Назад' из режима анализа — возвращаем пользователя в стандартный режим.
    """
    await state.set_state(UserStates.STANDARD)

    await message.answer(
        T.get("welcome_free"),
        reply_markup=main_menu_kb(),
    )


# 6. Текст в режиме PHOTO_COMMENT — комментарии и уточнения
@router.message(UserStates.PHOTO_COMMENT, F.text)
async def on_comment_text(message: Message, state: FSMContext):
    """
    Пользователь отправляет текст в режиме анализа фото.

    До первого анализа (нет last_analysis_type) — просто накапливаем комментарий,
    не трогаем GPT.

    После первого анализа — считаем каждое новое текстовое сообщение уточнением:
    - увеличиваем счётчик refinements_used
    - пересчитываем ответ GPT для последнего выбранного типа анализа
      (калорийность / рецепт) с учётом нового комментария.
    """
    data = await state.get_data()
    prev_comment = data.get("current_comment", "")
    last_analysis_type = data.get("last_analysis_type")
    refinements_used = int(data.get("refinements_used") or 0)

    # Обновляем общий комментарий (до или после анализа — всегда один источник правды)
    new_comment = (prev_comment + "\n" + message.text).strip()
    await state.update_data(current_comment=new_comment)

    # Если анализа ещё не было — просто копим комментарии
    if not last_analysis_type:
        await message.answer(
            T.get("refinement_hint"),  # “Можете дополнить описание…” и т.п.
            reply_markup=analysis_menu_kb(),
        )
        return

    # Здесь — уже были либо калорийность, либо рецепт → это уточнение

    if refinements_used >= MAX_REFINEMENTS_PER_PHOTO:
        # Лимит уточнений для этого фото исчерпан
        await message.answer(
            T.get("refinement_limit_reached"),
            reply_markup=analysis_menu_kb(),
        )
        return

    # Увеличиваем счётчик уточнений
    refinements_used += 1
    await state.update_data(refinements_used=refinements_used)

    await message.answer(T.get("analyzing_image"))

    try:
        # В зависимости от последнего анализа пересчитываем либо калорийность, либо рецепт
        if last_analysis_type == "nutrition":
            content = await analyze_nutrition_by_text(new_comment)
        elif last_analysis_type == "recipe":
            content = await analyze_recipe_by_text(new_comment)
        else:
            # На всякий случай fallback, но сюда мы не должны попадать
            content = T.get("analysis_error")

        content = content or T.get("analysis_error")

        await message.answer(content, reply_markup=analysis_menu_kb())

    except Exception as e:
        logger.exception("Ошибка при пересчёте GPT по уточнению: %s", e)
        await message.answer(
            T.get("analysis_error"),
            reply_markup=analysis_menu_kb(),
        )
