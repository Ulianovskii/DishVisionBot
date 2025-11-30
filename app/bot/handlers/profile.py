# app/bot/handlers/profile.py
from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton

from app.bot.states import UserStates
from app.locales.ru.buttons import RussianButtons as B
from app.locales.ru.texts import RussianTexts as T

router = Router()


def build_profile_keyboard(is_premium: bool = False) -> ReplyKeyboardMarkup:
    """
    Клавиатура профиля по ТЗ:
    - Анализировать еду
    - Помощь
    - Отчеты
    - План калорий
    - Купить премиум (если тариф бесплатный)
    """
    rows = [
        [
            KeyboardButton(text=B.get("analyze_food")),
            KeyboardButton(text=B.get("help")),
        ],
        [
            KeyboardButton(text=B.get("reports")),
            KeyboardButton(text=B.get("calorie_plan")),
        ],
    ]

    if not is_premium:
        rows.append([KeyboardButton(text=B.get("buy_premium"))])

    return ReplyKeyboardMarkup(
        keyboard=rows,
        resize_keyboard=True,
    )


@router.message(F.text == B.get("profile"))
async def on_profile_open(message: Message, state: FSMContext):
    # Профиль — это STATE_STANDARD
    await state.set_state(UserStates.STANDARD)

    # TODO: когда появятся лимиты и подписки — брать из БД
    # Пока всё жёстко захардкожено как бесплатный тариф с нулевым использованием
    is_premium = False
    photos_used_today = 0
    daily_limit = 5
    calorie_plan = None  # TODO: брать из БД

    # Тексты пока простые, потом можно вынести в RussianTexts
    text_lines = []

    if is_premium:
        text_lines.append("💎 Тариф: Премиум")
        # сюда потом добавим дату окончания
    else:
        text_lines.append("💼 Тариф: Бесплатный")

    text_lines.append(f"📸 Анализов сегодня: {photos_used_today} / {daily_limit}")

    if calorie_plan is None:
        text_lines.append("🎯 План по калориям: не задан")
    elif calorie_plan == 0:
        text_lines.append("🎯 План по калориям: не учитывается в отчетах")
    else:
        text_lines.append(f"🎯 План по калориям: {calorie_plan} Ккал")

    text_lines.append("")
    text_lines.append("Нажмите «План калорий», чтобы задать или изменить его.")

    await message.answer(
        "\n".join(text_lines),
        reply_markup=build_profile_keyboard(is_premium=is_premium),
    )


@router.message(F.text == B.get("calorie_plan"))
async def on_calorie_plan_start(message: Message, state: FSMContext):
    # Входим в режим ввода плана калорий
    await state.set_state(UserStates.CALORIES_PLAN)

    # Пока используем короткий текст, позже можно заменить на T.get("calories_plan_prompt")
    await message.answer(
        "🎯 Введите ваш дневной план по калориям.\n"
        "Отправьте одно число (Ккал) от 0 до 10000.\n\n"
        "0 — сбросить план (не учитывать в отчетах)."
    )

@router.message(UserStates.CALORIES_PLAN)
async def on_calorie_plan_input(message: Message, state: FSMContext):
    text = (message.text or "").strip()

    # 1. Парсим число
    try:
        value = int(text)
    except ValueError:
        await message.answer("❌ Ввести калории нужно целым числом от 0 до 10000.")
        return

    # 2. Проверяем диапазон
    if value < 0 or value > 10000:
        await message.answer("❌ Ввести калории нужно числом от 0 до 10000.")
        return

    # 3. Обработка 0 и 1..10000
    if value == 0:
        # TODO: сбросить план в БД
        await message.answer(
            "✅ План по калориям сброшен.\n"
            "В отчетах план учитываться не будет."
        )
    else:
        # TODO: сохранить план в БД
        await message.answer(
            f"🎯 План по калориям {value} Ккал сохранён.\n"
            "Позже это будет учитываться в отчетах."
        )

    # 4. Возвращаемся в STATE_STANDARD и снова открываем профиль
    await state.set_state(UserStates.STANDARD)

    # Пока считаем, что пользователь на бесплатном тарифе и план только что ввели
    await message.answer(
        "Профиль обновлён.",
        reply_markup=build_profile_keyboard(is_premium=False),
    )
