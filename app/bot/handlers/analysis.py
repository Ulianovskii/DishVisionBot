# app/bot/handlers/analysis.py

import logging
from datetime import date, datetime, timedelta, timezone

from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from app.bot.keyboards import analysis_menu_kb, main_menu_kb
from app.bot.states import UserStates
from app.locales.ru.texts import RussianTexts as T
from app.locales.ru.buttons import RussianButtons as B
from app.services.gpt_client import analyze_nutrition, analyze_recipe
from app.services.user_service import get_or_create_user
from app.services.limit_service import (
    get_limits_for_user,
    consume_photo_quota,
    get_user_today_analyses,
)
from app.config_limits import (
    PHOTO_SESSION_MAX_MESSAGES,
    PHOTO_SESSION_TIMEOUT_MINUTES,
    PRICE_PER_ANALYSIS,
)

router = Router()
logger = logging.getLogger(__name__)


def _normalize_to_utc(dt: datetime | None) -> datetime | None:
    """
    Приводим datetime к UTC-aware.
    Если None — возвращаем None.
    """
    if dt is None:
        return None

    if dt.tzinfo is None:
        # считаем, что это уже UTC без таймзоны
        return dt.replace(tzinfo=timezone.utc)

    return dt.astimezone(timezone.utc)


def _is_effective_premium(user) -> bool:
    """
    Пользователь считается премиумным, если:
    - is_premium = True и
    - premium_until либо не задан (бессрочный премиум), либо в будущем (UTC).
    """
    if not getattr(user, "is_premium", False):
        return False

    premium_until = _normalize_to_utc(getattr(user, "premium_until", None))
    now = datetime.now(timezone.utc)

    # premium_until=None → бессрочный премиум
    if premium_until is None:
        return True

    return premium_until > now



async def _download_photo_bytes(message: Message, file_id: str | None) -> bytes | None:
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


async def _ensure_session_active(message: Message, state: FSMContext) -> bool:
    data = await state.get_data()
    started_at_str = data.get("session_started_at")
    if not started_at_str:
        return True

    try:
        started_at = datetime.fromisoformat(started_at_str)
    except Exception:
        return True

    now = datetime.utcnow()
    if now - started_at > timedelta(minutes=PHOTO_SESSION_TIMEOUT_MINUTES):
        await state.clear()
        await state.set_state(UserStates.STANDARD)
        await message.answer(
            T.get("session_expired"),
            reply_markup=main_menu_kb(),
        )
        return False

    return True


async def _get_limits(message: Message) -> tuple[int, int]:
    """
    Возвращает (daily_limit, refinements_limit) для пользователя
    с учётом премиума.
    """
    telegram_id = message.from_user.id
    user = await get_or_create_user(telegram_id)
    is_premium = _is_effective_premium(user)
    return get_limits_for_user(is_premium)


async def _check_and_increment_daily_limit(
    message: Message,
    state: FSMContext,
    increment: bool,
) -> bool:
    """
    Проверяем дневной лимит анализов (фото) и, при необходимости, увеличиваем счётчик.

    increment = True — только для ПЕРВОГО анализа нового фото.
    Уточнения и повторные прогоны по тому же фото лимит не тратят.
    """
    if not increment:
        return True

    telegram_id = message.from_user.id
    user = await get_or_create_user(telegram_id)

    is_premium = _is_effective_premium(user)

    allowed, used, daily_limit = await consume_photo_quota(
        user_id=user.id,
        is_premium=is_premium,
    )

    if not allowed:
        await message.answer(
            T.get("daily_limit_exceeded").format(limit=daily_limit)
            + "\n"
            + T.get("buy_additional_analyses").format(
                number_of_analyses=PRICE_PER_ANALYSIS["number_of_analyses"],
                price=PRICE_PER_ANALYSIS["price"],
            ),
            reply_markup=main_menu_kb(),
        )
        await state.set_state(UserStates.STANDARD)
        return False

    logger.debug(
        "User %s used %s/%s daily photo analyses",
        telegram_id,
        used,
        daily_limit,
    )
    return True


async def _check_daily_limit(message: Message, state: FSMContext) -> bool:
    """
    Проверяет, исчерпан ли лимит анализов на сегодня,
    не изменяя счётчики.

    Используем при получении НОВОГО фото — до реального списания квоты.
    """
    telegram_id = message.from_user.id
    user = await get_or_create_user(telegram_id)

    is_premium = _is_effective_premium(user)
    daily_limit, _ = get_limits_for_user(is_premium)

    today = date.today()
    used_analyses = await get_user_today_analyses(user.id, today)

    if used_analyses >= daily_limit:
        await message.answer(
            T.get("daily_limit_exceeded").format(limit=daily_limit)
            + "\n"
            + T.get("buy_additional_analyses").format(
                number_of_analyses=PRICE_PER_ANALYSIS["number_of_analyses"],
                price=PRICE_PER_ANALYSIS["price"],
            ),
            reply_markup=main_menu_kb(),
        )
        await state.set_state(UserStates.STANDARD)
        return False

    return True


async def _run_analysis(
    message: Message,
    state: FSMContext,
    analysis_type: str,
    comment: str,
    count_for_daily_limit: bool,
    strip_questions: bool = False,
) -> None:
    if not await _ensure_session_active(message, state):
        return

    data = await state.get_data()
    photo_id = data.get("current_photo_file_id")

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

        calls = int(data.get("gpt_calls_for_current_photo", 0))
        await state.update_data(gpt_calls_for_current_photo=calls + 1)

    except Exception as e:
        logger.exception("Ошибка при вызове GPT (%s): %s", analysis_type, e)
        await message.answer(
            T.get("analysis_failed"),
            reply_markup=analysis_menu_kb(),
        )


# 1. Любое фото — старт анализа
@router.message(F.photo)
async def on_photo_received(message: Message, state: FSMContext):
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

    _, refinement_limit = await _get_limits(message)
    refinements_used = int(data.get("refinements_used", 0))

    if refinements_used >= refinement_limit:
        await message.answer(
            T.get("refinement_limit_reached"),
            reply_markup=analysis_menu_kb(disable_buttons=True),
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

    if recipe_used and nutrition_used:
        await message.answer(
            T.get("refinement_limit_reached"),
            reply_markup=analysis_menu_kb(),
        )
        return

    comment = (data.get("current_comment") or "").strip()
    calls = int(data.get("gpt_calls_for_current_photo", 0))
    count_for_daily_limit = calls == 0

    _, refinement_limit = await _get_limits(message)
    refinements_used = int(data.get("refinements_used", 0))

    if refinements_used >= refinement_limit:
        await message.answer(
            T.get("refinement_limit_reached"),
            reply_markup=analysis_menu_kb(disable_buttons=True),
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

    await state.set_state(UserStates.STANDARD)

    telegram_id = message.from_user.id
    user = await get_or_create_user(telegram_id)

    is_premium = _is_effective_premium(user)
    daily_limit, _ = get_limits_for_user(is_premium)

    today = date.today()
    used_analyses = await get_user_today_analyses(user.id, today)

    if used_analyses >= daily_limit:
        await message.answer(
            T.get("daily_limit_exceeded").format(limit=daily_limit)
            + "\n⭐️ "
            + T.get("buy_additional_analyses").format(
                number_of_analyses=PRICE_PER_ANALYSIS["number_of_analyses"],
                price=PRICE_PER_ANALYSIS["price"],
            ),
            reply_markup=main_menu_kb(),
        )
    else:
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


# 6. Текст в режиме PHOTO_COMMENT — уточнения / комментарии
# ВАЖНО: НЕ ПЕРЕХВАТЫВАЕМ КОМАНДЫ ("/superadmin" и т.п.)
@router.message(UserStates.PHOTO_COMMENT, F.text, ~F.text.startswith("/"))
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

    await state.update_data(current_comment=new_comment)

    messages_count = int(data.get("messages_count", 0)) + 1
    await state.update_data(messages_count=messages_count)

    last_type = data.get("last_analysis_type")
    calls = int(data.get("gpt_calls_for_current_photo", 0))

    if calls == 0 and messages_count >= PHOTO_SESSION_MAX_MESSAGES:
        if not last_type:
            last_type = "nutrition"
            await state.update_data(last_analysis_type=last_type)

        await message.answer(
            T.get("max_messages_for_photo"),
            reply_markup=analysis_menu_kb(),
        )

        await _run_analysis(
            message=message,
            state=state,
            analysis_type=last_type,
            comment=new_comment,
            count_for_daily_limit=True,
            strip_questions=False,
        )
        return

    if calls == 0 and not last_type:
        await message.answer(
            T.get("refinement_hint"),
            reply_markup=analysis_menu_kb(),
        )
        return

    _, refinement_limit = await _get_limits(message)
    refinements_used = int(data.get("refinements_used", 0))

    if refinements_used >= refinement_limit:
        await message.answer(
            T.get("refinement_limit_reached"),
            reply_markup=analysis_menu_kb(),
        )
        return

    refinements_used += 1
    await state.update_data(refinements_used=refinements_used)

    is_last = refinements_used >= refinement_limit

    await _run_analysis(
        message=message,
        state=state,
        analysis_type=last_type or "nutrition",
        comment=new_comment,
        count_for_daily_limit=False,
        strip_questions=is_last,
    )

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
