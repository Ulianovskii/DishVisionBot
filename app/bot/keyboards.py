from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

from app.locales.ru.buttons import RussianButtons as B


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
    )


def analysis_menu_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text=B.get("nutrition")),
                KeyboardButton(text=B.get("recipe")),
            ],
            [KeyboardButton(text=B.get("new_photo"))],
            [KeyboardButton(text=B.get("back"))],
        ],
        resize_keyboard=True,
    )


def profile_menu_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=B.get("set_calorie_goal"))],
            [KeyboardButton(text=B.get("back"))],
        ],
        resize_keyboard=True,
    )


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
