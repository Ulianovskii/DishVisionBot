# app/bot/handlers/analysis.py

# Стандартные библиотеки
import logging
from datetime import date, datetime, timedelta

# Сторонние библиотеки
from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

# Локальные модули
from app.bot.keyboards import analysis_menu_kb, main_menu_kb
from app.bot.states import UserStates
from app.locales.ru.texts import RussianTexts as T
from app.locales.ru.buttons import RussianButtons as B
from app.services.gpt_client import analyze_nutrition, analyze_recipe
from app.services.user_service import get_or_create_user, _is_premium_user
from app.services.limit_service import get_limits_for_user, consume_photo_quota
from app.config_limits import PHOTO_SESSION_MAX_MESSAGES, PHOTO_SESSION_TIMEOUT_MINUTES, PRICE_PER_ANALYSIS  # Импортируем цену за анализ




router = Router()
logger = logging.getLogger(__name__)

# Здесь используем функцию для проверки статуса пользователя
async def _is_premium_user(message: Message) -> bool:
    """
    Проверяем, является ли пользователь премиум. 
    Пока что используем фиктивную проверку для всех пользователей.
    Нужно заменить на реальную логику, которая проверяет в БД.
    """
    # Пример использования: в реальности вы будете проверять тарифы в базе данных
    telegram_id = message.from_user.id  # Берем ID пользователя из объекта message
    # Здесь ваш код для проверки, является ли пользователь премиум
    return False  # Предположим, что все пользователи не премиум

# Получаем лимит анализов и количество использованных анализов
async def _check_daily_limit(message: Message, state: FSMContext) -> bool:
    """
    Проверяет, исчерпан ли лимит бесплатных анализов на сегодня.
    Если лимит исчерпан, выводится сообщение о возможности покупки дополнительных анализов.
    Возвращает True, если можно продолжить анализ, иначе False.
    """
    telegram_id = message.from_user.id
    user = await get_or_create_user(telegram_id)

    # Получаем лимиты для пользователя
    is_premium = await _is_premium_user(message)
    daily_limit, _ = await get_limits_for_user(is_premium)

    # Получаем сегодня анализы из БД
    today = date.today()
    used_analyses = await get_user_today_analyses(user.id, today)

    if used_analyses >= daily_limit:
        # Лимит исчерпан — показываем сообщение о покупке дополнительных анализов
        await message.answer(
            T.get("daily_limit_exceeded").format(limit=daily_limit) + 
            f"\n⭐️ Вы можете купить {PRICE_PER_ANALYSIS['number_of_analyses']} анализов за {PRICE_PER_ANALYSIS['price']} звезд.",
            reply_markup=main_menu_kb()
        )
        return False
    return True


async def _run_analysis(
    message: Message,
    state: FSMContext,
    analysis_type: str,  # "nutrition" / "recipe"
    comment: str,
    count_for_daily_limit: bool,
    strip_questions: bool = False,
) -> None:
    """
    Общая функция: качаем фото, зовём GPT, показываем результат.
    """
    # Сначала проверяем, есть ли доступные анализы
    if not await _check_daily_limit(message, state):
        return  # Если лимит исчерпан, выходим

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

        if strip_questions:
            lines = result.splitlines()
            lines = [ln for ln in lines if not ln.lstrip().startswith("⁉️")]
            result = "\n".join(lines).strip()

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
    # Перед тем как продолжить, проверяем лимит
    if not await _check_daily_limit(message, state):
        return

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
        session_started_at=datetime.utcnow().isoformat(),
        messages_count=0,
    )

    await message.answer(
        T.get("photo_received_options"),
        reply_markup=analysis_menu_kb(),
    )


# 2. Кнопка "Калорийность"
@router.message(UserStates.PHOTO_COMMENT, F.text == B.get("nutrition"))
async def on_nutrition_request(message: Message, state: FSMContext):
    if not await _ensure_session_active(message, state):
        return

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
    count_for_daily_limit = calls == 0

    # Проверяем, исчерпан ли лимит уточнений
    _, refinement_limit = await _get_limits(message)
    refinements_used = int(data.get("refinements_used", 0))

    if refinements_used >= refinement_limit:
        # Скрываем кнопки "Калорийность" и "Рецепт"
        await message.answer(
            T.get("refinement_limit_reached_buttons_disabled"),
            reply_markup=analysis_menu_kb(disable_buttons=True, hide_nutrition_button=True, hide_recipe_button=False),  # Деактивируем кнопки
        )
        return

    strip_questions = refinements_used >= refinement_limit

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
        strip_questions=strip_questions,
    )


# 3. Кнопка "Рецепт"
@router.message(UserStates.PHOTO_COMMENT, F.text == B.get("recipe"))
async def on_recipe_request(message: Message, state: FSMContext):
    if not await _ensure_session_active(message, state):
        return

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

    # Проверка лимита уточнений
    _, refinement_limit = await _get_limits(message)
    refinements_used = int(data.get("refinements_used", 0))

    if refinements_used >= refinement_limit:
        # Скрываем кнопки "Калорийность" и "Рецепт"
        await message.answer(
            T.get("refinement_limit_reached_buttons_disabled"),
            reply_markup=analysis_menu_kb(disable_buttons=True, hide_nutrition_button=False, hide_recipe_button=True),  # Деактивируем кнопки
        )
        return

    strip_questions = refinements_used >= refinement_limit

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
        strip_questions=strip_questions,
    )


# 4. Кнопка "Новое фото"
@router.message(UserStates.PHOTO_COMMENT, F.text == B.get("new_photo"))
async def on_new_photo(message: Message, state: FSMContext):
    """
    Сбрасываем текущую сессию и просим прислать новое фото.
    """
    # Очистка состояния
    await state.set_state(UserStates.PHOTO_COMMENT)
    await state.update_data(
        current_photo_file_id=None,
        current_comment="",
        refinements_used=0,
        last_analysis_type=None,
        recipe_used=False,
        nutrition_used=False,
        gpt_calls_for_current_photo=0,
        session_started_at=datetime.utcnow().isoformat(),
        messages_count=0,
    )

    # Переводим в главное меню
    await state.set_state(UserStates.STANDARD)

    # Получаем лимиты
    telegram_id = message.from_user.id
    user = await get_or_create_user(telegram_id)
    is_premium = await _is_premium_user(message)
    daily_limit, _ = await get_limits_for_user(is_premium)

    # Получаем количество использованных анализов
    today = date.today()
    used_analyses = await get_user_today_analyses(user.id, today)

    if used_analyses >= daily_limit:
        # Лимит исчерпан
        await message.answer(
            T.get("daily_limit_exceeded").format(limit=daily_limit) + 
            f"\n⭐️ Вы можете купить {PRICE_PER_ANALYSIS['number_of_analyses']} анализов за {PRICE_PER_ANALYSIS['price']} звезд.",
            reply_markup=main_menu_kb()
        )
    else:
        # Если лимит не исчерпан, продолжаем анализ
        await message.answer(
            T.get("send_photo_for_analysis"),
            reply_markup=analysis_menu_kb()
        )


# 5. Кнопка "Назад" — в главное меню
@router.message(UserStates.PHOTO_COMMENT, F.text == B.get("back"))
async def on_back_to_main_from_photo(message: Message, state: FSMContext):
    await state.set_state(UserStates.STANDARD)

    await message.answer(
        T.get("welcome_free"),
        reply_markup=main_menu_kb(),
    )


# 6. Текст в режиме PHOTO_COMMENT — уточнения / комментарии
@router.message(UserStates.PHOTO_COMMENT, F.text)
async def on_comment_text(message: Message, state: FSMContext):
    """
    Пользователь пишет текст, пока открыта сессия анализа фото.

    Логика:
      - увеличиваем счётчик сообщений к фото
      - если достигли PHOTO_SESSION_MAX_MESSAGES и анализ ЕЩЁ НЕ запускали
        → автоматически запускаем первый анализ
      - иначе:
        * если анализ ещё не запускали — просто накапливаем комментарий и даём подсказку
        * если уже был анализ — считаем сообщение уточнением, проверяем лимит
          уточнений и пересчитываем последний выбранный тип анализа.
    """
    if not await _ensure_session_active(message, state):
        return

    data = await state.get_data()
    prev_comment = data.get("current_comment", "")
    new_comment = (prev_comment + "\n" + message.text).strip()

    # Обновляем комментарий
    await state.update_data(current_comment=new_comment)

    # Обновляем счётчик сообщений к фото
    messages_count = int(data.get("messages_count", 0)) + 1
    await state.update_data(messages_count=messages_count)

    last_type = data.get("last_analysis_type")
    calls = int(data.get("gpt_calls_for_current_photo", 0))

    # === 1. Принудительный анализ ТОЛЬКО до первого вызова GPT ===
    if calls == 0 and messages_count >= PHOTO_SESSION_MAX_MESSAGES:
        if not last_type:
            last_type = "nutrition"
            await state.update_data(last_analysis_type=last_type)

        await message.answer(
            T.get("max_messages_for_photo"),
            reply_markup=analysis_menu_kb(),
        )

        count_for_daily_limit = True  # это первый анализ для фото

        await _run_analysis(
            message=message,
            state=state,
            analysis_type=last_type,
            comment=new_comment,
            count_for_daily_limit=count_for_daily_limit,
            strip_questions=False,  # уточнения ещё будут, можно задавать вопросы
        )
        return

    # === 2. Анализ ещё не запускали — просто копим комментарии ===
    if calls == 0 and not last_type:
        await message.answer(
            T.get("refinement_hint"),
            reply_markup=analysis_menu_kb(),
        )
        return

    # === 3. Здесь уже был хотя бы один вызов GPT → работаем как "уточнения" ===

    _, refinement_limit = await _get_limits(message)
    refinements_used = int(data.get("refinements_used", 0))

    # Лимит уточнений уже исчерпан
    if refinements_used >= refinement_limit:
        await message.answer(
            T.get("refinement_limit_reached"),
            reply_markup=analysis_menu_kb(),
        )
        return

    refinements_used += 1
    await state.update_data(refinements_used=refinements_used)

    # Это последнее уточнение?
    is_last = refinements_used >= refinement_limit

    await _run_analysis(
        message=message,
        state=state,
        analysis_type=last_type or "nutrition",
        comment=new_comment,
        count_for_daily_limit=False,
        strip_questions=is_last,  # на последнем уточнении режем вопросы
    )

    # Показываем счётчик использованных уточнений
    remaining = refinement_limit - refinements_used
    if remaining > 0:
        await message.answer(
            T.get("refinement_counter").format(
                used=refinements_used,
                limit=refinement_limit,
            ),
            reply_markup=analysis_menu_kb(),
        )
    else:
        await message.answer(
            T.get("refinement_counter_last").format(
                used=refinements_used,
                limit=refinement_limit,
            ),
            reply_markup=analysis_menu_kb(),
        )
