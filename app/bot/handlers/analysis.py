# app/bot/handlers/analysis.py

import logging
from datetime import date

from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from app.bot.keyboards import analysis_menu_kb, main_menu_kb
from app.bot.states import UserStates
from app.locales.ru.texts import RussianTexts as T
from app.locales.ru.buttons import RussianButtons as B
from app.services.gpt_client import analyze_nutrition, analyze_recipe

router = Router()
logger = logging.getLogger(__name__)

# Лимиты из 06_abuse_protection.md
MAX_DAILY_ANALYSES_FREE = 5
MAX_DAILY_ANALYSES_PREMIUM = 15

MAX_REFINEMENTS_FREE = 2
MAX_REFINEMENTS_PREMIUM = 5


async def _is_premium_user(message: Message) -> bool:
    """
    TODO: здесь надо будет подтянуть реальный тариф из БД.
    Пока считаем, что все пользователи на бесплатном тарифе.
    """
    return False


async def _get_limits(message: Message) -> tuple[int, int]:
    is_premium = await _is_premium_user(message)
    daily = MAX_DAILY_ANALYSES_PREMIUM if is_premium else MAX_DAILY_ANALYSES_FREE
    refinements = (
        MAX_REFINEMENTS_PREMIUM if is_premium else MAX_REFINEMENTS_FREE
    )
    return daily, refinements


async def _check_and_increment_daily_limit(
    message: Message,
    state: FSMContext,
    increment: bool,
) -> bool:
    """
    Проверяем дневной лимит анализов (фото) и, если нужно, увеличиваем счётчик.

    increment = True — только для первого анализа нового фото.
    Уточнения и повторные прогоны по тому же фото лимит не трогают.
    """
    if not increment:
        return True

    data = await state.get_data()
    today = date.today().isoformat()
    stored_date = data.get("daily_analyses_date")
    used_today = int(data.get("daily_analyses_used", 0))

    daily_limit, _ = await _get_limits(message)

    # День сменился — обнуляем
    if stored_date != today:
        stored_date = today
        used_today = 0

    if used_today >= daily_limit:
        await message.answer(
            T.get("daily_limit_exceeded").format(limit=daily_limit),
            reply_markup=main_menu_kb(),
        )
        await state.update_data(
            daily_analyses_date=stored_date,
            daily_analyses_used=used_today,
        )
        return False

    used_today += 1
    await state.update_data(
        daily_analyses_date=stored_date,
        daily_analyses_used=used_today,
    )
    return True


async def _download_photo_bytes(message: Message, file_id: str | None) -> bytes | None:
    """
    Скачиваем фото по file_id из Telegram.
    """
    if not file_id:
        await message.answer(T.get("photo_not_found"))
        return None

    try:
        file_io = await message.bot.download(file_id)
        if hasattr(file_io, "getvalue"):
            return file_io.getvalue()
        return file_io.read()
    except Exception as e:
        logger.exception("Не удалось скачать фото %s: %s", file_id, e)
        await message.answer(T.get("analysis_failed"))
        return None


async def _run_analysis(
    message: Message,
    state: FSMContext,
    analysis_type: str,  # "nutrition" / "recipe"
    comment: str,
    count_for_daily_limit: bool,
) -> None:
    """
    Общая функция: качаем фото, зовём GPT, показываем результат.
    """
    data = await state.get_data()
    photo_id = data.get("current_photo_file_id")

    # Проверка дневного лимита (только для первого анализа фото)
    can_run = await _check_and_increment_daily_limit(
        message, state, increment=count_for_daily_limit
    )
    if not can_run:
        return

    image_bytes = await _download_photo_bytes(message, photo_id)
    if image_bytes is None:
        return

    await message.answer(T.get("analyzing_image"))

    try:
        if analysis_type == "nutrition":
            result = await analyze_nutrition(image_bytes, comment or None)
        else:
            result = await analyze_recipe(image_bytes, comment or None)

        if not result:
            result = T.get("analysis_failed")

        await message.answer(result, reply_markup=analysis_menu_kb())

        # увеличиваем счётчик вызовов GPT для текущего фото
        calls = int(data.get("gpt_calls_for_current_photo", 0))
        await state.update_data(gpt_calls_for_current_photo=calls + 1)

    except Exception as e:
        logger.exception("Ошибка при вызове GPT (%s): %s", analysis_type, e)
        await message.answer(
            T.get("analysis_failed"),
            reply_markup=analysis_menu_kb(),
        )


# 1. Любое фото — старт анализа (с подписью или без)
@router.message(F.photo)
async def on_photo_received(message: Message, state: FSMContext):
    """
    Пользователь прислал новое фото — начинаем новую сессию анализа.
    Caption используем как первичный комментарий (не считается уточнением).
    """
    photo = message.photo[-1]
    file_id = photo.file_id
    initial_comment = (message.caption or "").strip() if message.caption else ""

    await state.set_state(UserStates.PHOTO_COMMENT)
    await state.update_data(
        current_photo_file_id=file_id,
        current_comment=initial_comment,
        refinements_used=0,
        last_analysis_type=None,
        recipe_used=False,
        nutrition_used=False,
        gpt_calls_for_current_photo=0,
    )

    await message.answer(
        T.get("photo_received_options"),
        reply_markup=analysis_menu_kb(),
    )


# 2. Кнопка "Калорийность"
@router.message(UserStates.PHOTO_COMMENT, F.text == B.get("nutrition"))
async def on_nutrition_request(message: Message, state: FSMContext):
    data = await state.get_data()
    photo_id = data.get("current_photo_file_id")

    if not photo_id:
        await message.answer(
            T.get("photo_first_then_text"),
            reply_markup=analysis_menu_kb(),
        )
        return

    comment = (data.get("current_comment") or "").strip()
    calls = int(data.get("gpt_calls_for_current_photo", 0))
    # Первый анализ этого фото — учитываем в дневном лимите
    count_for_daily_limit = calls == 0

    await state.update_data(
        last_analysis_type="nutrition",
        nutrition_used=True,
    )

    await _run_analysis(
        message=message,
        state=state,
        analysis_type="nutrition",
        comment=comment,
        count_for_daily_limit=count_for_daily_limit,
    )


# 3. Кнопка "Рецепт"
@router.message(UserStates.PHOTO_COMMENT, F.text == B.get("recipe"))
async def on_recipe_request(message: Message, state: FSMContext):
    data = await state.get_data()
    photo_id = data.get("current_photo_file_id")

    if not photo_id:
        await message.answer(
            T.get("photo_first_then_text"),
            reply_markup=analysis_menu_kb(),
        )
        return

    recipe_used = bool(data.get("recipe_used"))
    nutrition_used = bool(data.get("nutrition_used"))

    # Логика из описания:
    # если уже был рецепт И уже была калорийность — обратно к рецепту не пускаем
    if recipe_used and nutrition_used:
        await message.answer(
            T.get("refinement_limit_reached"),
            reply_markup=analysis_menu_kb(),
        )
        return

    comment = (data.get("current_comment") or "").strip()
    calls = int(data.get("gpt_calls_for_current_photo", 0))
    count_for_daily_limit = calls == 0

    await state.update_data(
        last_analysis_type="recipe",
        recipe_used=True,
    )

    await _run_analysis(
        message=message,
        state=state,
        analysis_type="recipe",
        comment=comment,
        count_for_daily_limit=count_for_daily_limit,
    )


# 4. Кнопка "Новое фото"
@router.message(UserStates.PHOTO_COMMENT, F.text == B.get("new_photo"))
async def on_new_photo(message: Message, state: FSMContext):
    """
    Сбрасываем текущую сессию и просим прислать новое фото.
    """
    await state.update_data(
        current_photo_file_id=None,
        current_comment="",
        refinements_used=0,
        last_analysis_type=None,
        recipe_used=False,
        nutrition_used=False,
        gpt_calls_for_current_photo=0,
    )

    await message.answer(
        T.get("send_photo_for_analysis"),
        reply_markup=analysis_menu_kb(),
    )


# 5. Кнопка "Назад" — в главное меню
@router.message(UserStates.PHOTO_COMMENT, F.text == B.get("back"))
async def on_back_to_main_from_photo(message: Message, state: FSMContext):
    await state.set_state(UserStates.STANDARD)

    await message.answer(
        T.get("welcome_free"),
        reply_markup=main_menu_kb(),
    )


# 6. Текст в режиме PHOTO_COMMENT — уточнения
@router.message(UserStates.PHOTO_COMMENT, F.text)
async def on_comment_text(message: Message, state: FSMContext):
    """
    Пользователь пишет текст, пока открыта сессия анализа фото.

    Если анализ ещё не запускали — просто накапливаем комментарий.
    Если уже был вызван "Рецепт" или "Калорийность" — считаем сообщение уточнением:
      - проверяем лимит уточнений по тарифу
      - пересчитываем последний выбранный тип анализа
    """
    data = await state.get_data()
    prev_comment = data.get("current_comment", "")
    new_comment = (prev_comment + "\n" + message.text).strip()

    _, refinement_limit = await _get_limits(message)
    refinements_used = int(data.get("refinements_used", 0))
    last_type = data.get("last_analysis_type")

    # Обновляем комментарий в любом случае
    await state.update_data(current_comment=new_comment)

    # Анализ ещё не запускали — просто подсказываем, что делать дальше
    if not last_type:
        await message.answer(
            T.get("refinement_hint"),
            reply_markup=analysis_menu_kb(),
        )
        return

    # Лимит уточнений уже исчерпан
    if refinements_used >= refinement_limit:
        await message.answer(
            T.get("refinement_limit_reached"),
            reply_markup=analysis_menu_kb(),
        )
        return

    refinements_used += 1
    await state.update_data(refinements_used=refinements_used)

    # Уточнения дневной лимит не тратят
    await _run_analysis(
        message=message,
        state=state,
        analysis_type=last_type,
        comment=new_comment,
        count_for_daily_limit=False,
    )

    # Показываем счётчик использованных уточнений
    await message.answer(
        T.get("refinement_counter").format(
            used=refinements_used,
            limit=refinement_limit,
        ),
        reply_markup=analysis_menu_kb(),
    )
