# app/bot/keyboards.py

from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from app.locales.ru.buttons import RussianButtons as B


# ===== Главное меню =====
def main_menu_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=B.get("analyze_food"))],
            [
                KeyboardButton(text=B.get("profile")),
                KeyboardButton(text=B.get("reports")),
            ],
            [KeyboardButton(text=B.get("buy_premium"))],
            [KeyboardButton(text=B.get("help"))],
        ],
        resize_keyboard=True,
        is_persistent=True,
    )


# ===== Меню анализа =====
def analysis_menu_kb(disable_buttons=False) -> ReplyKeyboardMarkup:
    keyboard = []

    if not disable_buttons:
        keyboard.append([
            KeyboardButton(text=B.get("nutrition")),
            KeyboardButton(text=B.get("recipe")),
        ])

    keyboard.append([KeyboardButton(text=B.get("new_photo"))])
    keyboard.append([KeyboardButton(text=B.get("back"))])

    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)


# ===== Профиль =====
def profile_menu_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=B.get("set_calorie_goal"))],
            [KeyboardButton(text=B.get("back"))],
        ],
        resize_keyboard=True,
    )


# ===== Отчёты =====
def reports_menu_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text=B.get("report_day")),
                KeyboardButton(text=B.get("report_week")),
                KeyboardButton(text=B.get("report_month")),
            ],
            [KeyboardButton(text=B.get("back"))],
        ],
        resize_keyboard=True,
    )


# ===== Премиум =====
def premium_menu_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text=B.get("buy_week_confirm")),
                KeyboardButton(text=B.get("buy_month_confirm")),
            ],
            [KeyboardButton(text=B.get("enter_promo"))],
            [KeyboardButton(text=B.get("back"))],
        ],
        resize_keyboard=True,
    )


# ====================================================
#                   АДМИНКА
# ====================================================

# Главное админ-меню
def admin_menu_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=B.get("admin_statistics"))],
            [KeyboardButton(text=B.get("admin_manage_limits"))],
            [KeyboardButton(text=B.get("admin_promo"))],
            [KeyboardButton(text=B.get("admin_exit"))],
        ],
        resize_keyboard=True,
    )


# Подменю — Управление лимитами
def admin_limits_menu_kb() -> ReplyKeyboardMarkup:
    """
    Подменю 'Управление лимитами' в админке.
    """
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=B.get("admin_limits_reset_me"))],
            [
                KeyboardButton(text=B.get("admin_premium_on_me")),
                KeyboardButton(text=B.get("admin_premium_off_me")),
            ],
            [KeyboardButton(text=B.get("admin_limits_reset_other"))],
            [KeyboardButton(text=B.get("back"))],
        ],
        resize_keyboard=True,
    )