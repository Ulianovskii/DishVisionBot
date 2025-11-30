# app/bot/handlers/admin.py
from __future__ import annotations

from typing import Optional

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy import delete, select

from app.db.base import AsyncSessionLocal        # ✅ используем то же, что в сервисах
from app.db import models                        # ✅ модели из models.py
from app.locales.ru.texts import RussianTexts as T

router = Router(name="admin")

# Админские telegram_id (можно потом вынести в БД admin_users)
ADMIN_IDS: set[int] = {
    103181087,  # твой id
}


class AdminStates(StatesGroup):
    waiting_for_telegram_id_for_limit_reset = State()


def _is_admin_tg_id(tg_id: Optional[int]) -> bool:
    if tg_id is None:
        return False
    return tg_id in ADMIN_IDS


def _admin_main_keyboard():
    """
    Главное меню админки (inline-кнопки).
    Сейчас один раздел — управление лимитами.
    """
    kb = InlineKeyboardBuilder()
    kb.button(text="Управление лимитами и премиумом", callback_data="admin_limits")
    return kb.as_markup()


def _admin_limits_keyboard():
    """
    Клавиатура внутри раздела "Управление лимитами и премиумом".
    """
    kb = InlineKeyboardBuilder()
    kb.button(
        text="🔁 Сбросить мои лимиты",
        callback_data="admin_limits_reset_me",
    )
    kb.button(
        text="⭐ Включить мой премиум",
        callback_data="admin_premium_on_me",
    )
    kb.button(
        text="🚫 Выключить мой премиум",
        callback_data="admin_premium_off_me",
    )
    kb.button(
        text="👤 Сброс лимитов по telegram_id",
        callback_data="admin_limits_reset_other",
    )
    kb.button(text="⬅️ Назад", callback_data="admin_back_to_main")
    kb.adjust(1)
    return kb.as_markup()


# ===== Вход в админку =====

@router.message(Command("admin"))
async def admin_entry(message: Message, db_user: models.User):
    """
    Вход в админку. Доступен только администраторам.
    UserMiddleware уже создал пользователя и положил его в data["db_user"],
    поэтому сюда прилетает db_user.
    """
    if not _is_admin_tg_id(message.from_user.id if message.from_user else None):
        await message.answer(T.get("admin_access_denied"))
        return

    await message.answer(
        T.get("admin_menu_welcome"),
        reply_markup=_admin_main_keyboard(),
    )


@router.callback_query(F.data == "admin_back_to_main")
async def admin_back_to_main(callback: CallbackQuery):
    """
    Возврат в главное меню админки.
    """
    if not _is_admin_tg_id(callback.from_user.id if callback.from_user else None):
        await callback.answer(T.get("admin_access_denied"), show_alert=True)
        return

    await callback.message.edit_text(
        T.get("admin_menu_welcome"),
        reply_markup=_admin_main_keyboard(),
    )
    await callback.answer()


# ===== Меню "Управление лимитами" =====

@router.callback_query(F.data == "admin_limits")
async def admin_open_limits(callback: CallbackQuery):
    """
    Меню «Управление лимитами и премиумом».
    """
    if not _is_admin_tg_id(callback.from_user.id if callback.from_user else None):
        await callback.answer(T.get("admin_access_denied"), show_alert=True)
        return

    await callback.message.edit_text(
        T.get("admin_limits_menu_title"),
        reply_markup=_admin_limits_keyboard(),
    )
    await callback.answer()


# ===== Сброс лимитов для себя =====

@router.callback_query(F.data == "admin_limits_reset_me")
async def admin_limits_reset_me(callback: CallbackQuery, db_user: models.User):
    """
    Сброс лимитов для самого себя (админа).
    Просто удаляем все записи из user_limits по user_id.
    """
    if not _is_admin_tg_id(callback.from_user.id if callback.from_user else None):
        await callback.answer(T.get("admin_access_denied"), show_alert=True)
        return

    async with AsyncSessionLocal() as session:
        await session.execute(
            delete(models.UserLimit).where(models.UserLimit.user_id == db_user.id)
        )
        await session.commit()

    await callback.answer(T.get("admin_limits_reset_me_done"))


# ===== Включить/выключить премиум себе =====

@router.callback_query(F.data == "admin_premium_on_me")
async def admin_premium_on_me(callback: CallbackQuery, db_user: models.User):
    """
    Включить премиум для себя.
    Делаем бессрочный премиум (premium_until = None).
    """
    if not _is_admin_tg_id(callback.from_user.id if callback.from_user else None):
        await callback.answer(T.get("admin_access_denied"), show_alert=True)
        return

    async with AsyncSessionLocal() as session:
        user = await session.get(models.User, db_user.id)
        if not user:
            await callback.answer(T.get("admin_user_not_found"), show_alert=True)
            return

        user.is_premium = True
        user.premium_until = None  # бессрочный премиум

        await session.commit()

    await callback.answer(T.get("admin_premium_on_me_done"))


@router.callback_query(F.data == "admin_premium_off_me")
async def admin_premium_off_me(callback: CallbackQuery, db_user: models.User):
    """
    Выключить премиум для себя.
    """
    if not _is_admin_tg_id(callback.from_user.id if callback.from_user else None):
        await callback.answer(T.get("admin_access_denied"), show_alert=True)
        return

    async with AsyncSessionLocal() as session:
        user = await session.get(models.User, db_user.id)
        if not user:
            await callback.answer(T.get("admin_user_not_found"), show_alert=True)
            return

        user.is_premium = False
        user.premium_until = None

        await session.commit()

    await callback.answer(T.get("admin_premium_off_me_done"))


# ===== Сброс лимитов по telegram_id =====

@router.callback_query(F.data == "admin_limits_reset_other")
async def admin_limits_reset_other_start(callback: CallbackQuery, state: FSMContext):
    """
    Начинаем сценарий сброса лимитов по telegram_id.
    """
    if not _is_admin_tg_id(callback.from_user.id if callback.from_user else None):
        await callback.answer(T.get("admin_access_denied"), show_alert=True)
        return

    await state.set_state(AdminStates.waiting_for_telegram_id_for_limit_reset)
    await callback.message.edit_text(T.get("admin_limit_reset_prompt"))
    await callback.answer()


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
        user = await session.scalar(
            select(models.User).where(models.User.telegram_id == target_telegram_id)
        )
        if not user:
            await message.answer(T.get("admin_user_not_found"))
            await state.clear()
            return

        await session.execute(
            delete(models.UserLimit).where(models.UserLimit.user_id == user.id)
        )
        await session.commit()

    await message.answer(
        T.get("admin_limits_reset", user_id=target_telegram_id)
    )
    await state.clear()
