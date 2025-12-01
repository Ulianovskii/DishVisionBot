from aiogram.types import (
    ReplyKeyboardMarkup,
    KeyboardButton,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)
from app.locales.ru.buttons import RussianButtons as B


# ====================================================
#                   ГЛАВНОЕ МЕНЮ
# ====================================================

def main_menu_kb() -> ReplyKeyboardMarkup:
    """
    Главное меню: Анализ, Профиль, Премиум, Помощь.
    Кнопки сгруппированы так, чтобы не занимать слишком много места по вертикали.
    """
    return ReplyKeyboardMarkup(
        keyboard=[
            # Главная целевая кнопка — отдельной строкой
            [KeyboardButton(text=B.get("analyze_food"))],
            # Профиль + Премиум в одной строке
            [
                KeyboardButton(text=B.get("profile")),
                KeyboardButton(text=B.get("buy_premium")),
            ],
            # Помощь отдельной строкой внизу
            [KeyboardButton(text=B.get("help"))],
        ],
        resize_keyboard=True,
        is_persistent=True,
    )


# ====================================================
#                   МЕНЮ АНАЛИЗА
# ====================================================

def analysis_menu_kb(disable_buttons: bool = False) -> ReplyKeyboardMarkup:
    """
    Меню анализа (когда фото уже загружено).
    """
    keyboard = []

    if not disable_buttons:
        keyboard.append(
            [
                KeyboardButton(text=B.get("nutrition")),
                KeyboardButton(text=B.get("recipe")),
            ]
        )

    keyboard.append([KeyboardButton(text=B.get("new_photo"))])
    keyboard.append([KeyboardButton(text=B.get("back"))])

    return ReplyKeyboardMarkup(
        keyboard=keyboard,
        resize_keyboard=True,
    )


# ====================================================
#                   ПРОФИЛЬ (старое меню)
# ====================================================

def profile_menu_kb() -> ReplyKeyboardMarkup:
    """
    Оставлено только на будущее.
    Сейчас НЕ используется — клавиатура профиля
    формируется в build_profile_keyboard().
    """
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=B.get("back"))],
        ],
        resize_keyboard=True,
    )


# ====================================================
#                       ОТЧЁТЫ
# ====================================================

def reports_menu_kb() -> ReplyKeyboardMarkup:
    """
    Меню отчётов.
    Сейчас недостижимо для пользователя, потому что
    кнопка 'Отчеты' скрыта из главного меню.
    """
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


# ====================================================
#               ПРЕМИУМ-ПОДПИСКА
# ====================================================

def premium_menu_kb() -> ReplyKeyboardMarkup:
    """
    Меню оформления премиума.
    """
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
#           ИНЛАЙН-КЛАВИАТУРА ПОКУПКИ ЛИМИТОВ
# ====================================================

def buy_more_analyses_inline_kb() -> InlineKeyboardMarkup:
    """
    Инлайн-кнопка для покупки дополнительного пакета анализов.
    """
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Купить 5 анализов ⭐",
                    callback_data="buy_analyses_pack",
                )
            ]
        ]
    )


# ====================================================
#                       АДМИНКА
# ====================================================

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


def admin_limits_menu_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=B.get("admin_limits_reset_me"))],
            [
                KeyboardButton(text=B.get("admin_premium_on_me")),
                KeyboardButton(text=B.get("admin_premium_off_me")),
            ],
            [KeyboardButton(text=B.get("admin_limits_reset_other"))],
            [KeyboardButton(text=B.get("admin_limits_back"))],
        ],
        resize_keyboard=True,
    )
