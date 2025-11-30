# app/bot/handlers/admin.py

from __future__ import annotations

from typing import Optional, Set

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import Message
from sqlalchemy import delete, select

from app.config import settings
from app.bot.keyboards import (
    admin_menu_kb,
    admin_limits_menu_kb,
    main_menu_kb,
)
from app.locales.ru.texts import RussianTexts as T
from app.locales.ru.buttons import RussianButtons as B
from app.db.base import AsyncSessionLocal
from app.db import models
from app.services.promo_service import generate_promo_codes

router = Router(name="admin")


# ===== Разбор ADMIN_USER_IDS из .env =====

def _load_admin_ids() -> Set[int]:
    raw = getattr(settings, "admin_user_ids", "") or ""
    ids: Set[int] = set()
    for part in raw.split(","):
        part = part.strip()
        if not part:
            continue
        try:
            ids.add(int(part))
        except ValueError:
            continue
    return ids


ADMIN_IDS: Set[int] = _load_admin_ids()


def _is_admin_tg_id(tg_id: Optional[int]) -> bool:
    if tg_id is None:
        return False
    return tg_id in ADMIN_IDS


# ===== FSM-состояния для админки =====

class AdminStates(StatesGroup):
    waiting_for_telegram_id_for_limit_reset = State()
    waiting_for_promo_count = State()


# ===== Вход в админку =====

@router.message(Command("superadmin"))
async def admin_entry(message: Message, state: FSMContext):
    """
    Вход в админ-меню. Одна команда: /superadmin.
    """
    if not _is_admin_tg_id(message.from_user.id if message.from_user else None):
        await message.answer(T.get("admin_access_denied"))
        return

    await state.clear()
    await message.answer(
        T.get("admin_menu_welcome"),
        reply_markup=admin_menu_kb(),
    )


# ===== Раздел "Статистика" (пока заглушка) =====

@router.message(F.text == B.get("admin_statistics"))
async def admin_statistics_placeholder(message: Message):
    if not _is_admin_tg_id(message.from_user.id if message.from_user else None):
        return

    await message.answer(
        T.get("admin_statistics_placeholder"),
        reply_markup=admin_menu_kb(),
    )


# ===== Раздел "Управление лимитами" =====

@router.message(F.text == B.get("admin_manage_limits"))
async def admin_open_limits(message: Message):
    """
    Открываем подменю управления лимитами и премиумом.
    """
    if not _is_admin_tg_id(message.from_user.id if message.from_user else None):
        return

    await message.answer(
        T.get("admin_limits_menu_title"),
        reply_markup=admin_limits_menu_kb(),
    )


@router.message(F.text == B.get("admin_limits_reset_me"))
async def admin_limits_reset_me(message: Message):
    """
    Сброс лимитов для самого себя.
    """
    if not _is_admin_tg_id(message.from_user.id if message.from_user else None):
        return

    async with AsyncSessionLocal() as session:
        # ищем пользователя по telegram_id
        stmt = select(models.User).where(
            models.User.telegram_id == message.from_user.id
        )
        res = await session.execute(stmt)
        user = res.scalar_one_or_none()

        if not user:
            await message.answer(T.get("admin_user_not_found"))
            return

        await session.execute(
            delete(models.UserLimit).where(models.UserLimit.user_id == user.id)
        )
        await session.commit()

    await message.answer(
        T.get("admin_limits_reset_me_done"),
        reply_markup=admin_limits_menu_kb(),
    )


@router.message(F.text == B.get("admin_premium_on_me"))
async def admin_premium_on_me(message: Message):
    """
    Включить себе премиум (бессрочно).
    """
    if not _is_admin_tg_id(message.from_user.id if message.from_user else None):
        return

    async with AsyncSessionLocal() as session:
        stmt = select(models.User).where(
            models.User.telegram_id == message.from_user.id
        )
        res = await session.execute(stmt)
        user = res.scalar_one_or_none()

        if not user:
            await message.answer(T.get("admin_user_not_found"))
            return

        user.is_premium = True
        user.premium_until = None  # бессрочный премиум
        await session.commit()

    await message.answer(
        T.get("admin_premium_on_me_done"),
        reply_markup=admin_limits_menu_kb(),
    )


@router.message(F.text == B.get("admin_premium_off_me"))
async def admin_premium_off_me(message: Message):
    """
    Выключить себе премиум.
    """
    if not _is_admin_tg_id(message.from_user.id if message.from_user else None):
        return

    async with AsyncSessionLocal() as session:
        stmt = select(models.User).where(
            models.User.telegram_id == message.from_user.id
        )
        res = await session.execute(stmt)
        user = res.scalar_one_or_none()

        if not user:
            await message.answer(T.get("admin_user_not_found"))
            return

        user.is_premium = False
        user.premium_until = None
        await session.commit()

    await message.answer(
        T.get("admin_premium_off_me_done"),
        reply_markup=admin_limits_menu_kb(),
    )


@router.message(F.text == B.get("admin_limits_reset_other"))
async def admin_limits_reset_other_start(message: Message, state: FSMContext):
    """
    Начало сценария сброса лимитов по telegram_id.
    """
    if not _is_admin_tg_id(message.from_user.id if message.from_user else None):
        return

    await state.set_state(AdminStates.waiting_for_telegram_id_for_limit_reset)
    await message.answer(T.get("admin_limit_reset_prompt"))


@router.message(AdminStates.waiting_for_telegram_id_for_limit_reset)
async def admin_limits_reset_other_process(message: Message, state: FSMContext):
    """
    Обработка введённого telegram_id для сброса лимитов.
    """
    if not _is_admin_tg_id(message.from_user.id if message.from_user else None):
        await state.clear()
        return

    text = (message.text or "").strip()

    try:
        target_telegram_id = int(text)
    except ValueError:
        await message.answer(T.get("admin_limits_telegram_id_must_be_int"))
        return

    async with AsyncSessionLocal() as session:
        stmt = select(models.User).where(
            models.User.telegram_id == target_telegram_id
        )
        res = await session.execute(stmt)
        user = res.scalar_one_or_none()

        if not user:
            await message.answer(T.get("admin_user_not_found"))
            await state.clear()
            return

        await session.execute(
            delete(models.UserLimit).where(models.UserLimit.user_id == user.id)
        )
        await session.commit()

    await state.clear()
    # Без вывода конкретного telegram_id, чтобы ничего не светить в текстах
    await message.answer(
        T.get("admin_limits_reset_me_done"),
        reply_markup=admin_limits_menu_kb(),
    )

@router.message(F.text == B.get("admin_limits_back"))
async def admin_limits_back_to_menu(message: Message, state: FSMContext):
    """
    Назад из подменю лимитов в главное админ-меню.
    Не выкидывает в обычную главную, остаёмся в админке.
    """
    if not _is_admin_tg_id(message.from_user.id if message.from_user else None):
        return

    # На всякий случай очищаем состояние, чтобы не висеть в сценарии ввода ID/количества
    await state.clear()

    await message.answer(
        T.get("admin_menu_welcome"),
        reply_markup=admin_menu_kb(),
    )


# ===== Раздел "Промокоды" =====

@router.message(F.text == B.get("admin_promo"))
async def admin_promo_start(message: Message, state: FSMContext):
    """
    Запускаем сценарий генерации промокодов.
    """
    if not _is_admin_tg_id(message.from_user.id if message.from_user else None):
        return

    await state.set_state(AdminStates.waiting_for_promo_count)
    await message.answer(T.get("admin_promo_generate_prompt"))


@router.message(AdminStates.waiting_for_promo_count)
async def admin_promo_generate(message: Message, state: FSMContext):
    """
    Принимаем количество промокодов, генерируем и выводим список.
    """
    if not _is_admin_tg_id(message.from_user.id if message.from_user else None):
        await state.clear()
        return

    text = (message.text or "").strip()

    try:
        count = int(text)
    except ValueError:
        await message.answer(T.get("admin_promo_generate_prompt"))
        return

    if count < 1 or count > 10:
        await message.answer(T.get("admin_promo_generate_prompt"))
        return

    # Пример: генерируем промокоды на 7 дней премиума
    codes = await generate_promo_codes(
        count=count,
        days=7,
        created_by=message.from_user.id,
        expires_at=None,
    )

    await state.clear()

    codes_str = "\n".join(codes)
    await message.answer(
        T.get("admin_promo_generated", codes=codes_str),
        reply_markup=admin_menu_kb(),
    )


# ===== Выход из админки =====

@router.message(F.text == B.get("admin_exit"))
async def admin_exit(message: Message, state: FSMContext):
    """
    Выход из админ-меню: возвращаем обычное главное меню бота.
    """
    if not _is_admin_tg_id(message.from_user.id if message.from_user else None):
        return

    await state.clear()
    await message.answer(
        T.get("admin_exit_message"),
        reply_markup=main_menu_kb(),
    )
