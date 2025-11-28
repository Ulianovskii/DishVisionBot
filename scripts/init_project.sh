#!/usr/bin/env bash
set -e

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo "Project root: $PROJECT_ROOT"

mkdir -p "$PROJECT_ROOT/app/bot/handlers"
mkdir -p "$PROJECT_ROOT/app/locales/ru"
mkdir -p "$PROJECT_ROOT/app/prompts"
mkdir -p "$PROJECT_ROOT/app/db"
mkdir -p "$PROJECT_ROOT/app/services"
mkdir -p "$PROJECT_ROOT/docs"

touch "$PROJECT_ROOT/app/__init__.py"
touch "$PROJECT_ROOT/app/bot/__init__.py"
touch "$PROJECT_ROOT/app/bot/handlers/__init__.py"
touch "$PROJECT_ROOT/app/locales/__init__.py"
touch "$PROJECT_ROOT/app/locales/ru/__init__.py"
touch "$PROJECT_ROOT/app/prompts/__init__.py"
touch "$PROJECT_ROOT/app/db/__init__.py"
touch "$PROJECT_ROOT/app/services/__init__.py"

# config.py
cat > "$PROJECT_ROOT/app/config.py" << 'PYEOF'
from pydantic import BaseSettings


class Settings(BaseSettings):
    bot_token: str
    openai_api_key: str

    default_language: str = "ru"
    log_level: str = "INFO"
    api_timeout: int = 30
    max_file_size: int = 10 * 1024 * 1024  # 10MB

    database_url: str
    admin_user_ids: str = ""

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


settings = Settings()
PYEOF

# main.py — минимальный живой бот
cat > "$PROJECT_ROOT/app/main.py" << 'PYEOF'
import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.filters import CommandStart, Command
from aiogram.types import Message

from app.config import settings
from app.locales.ru.texts import RussianTexts
from app.locales.ru.buttons import RussianButtons


dp = Dispatcher()


@dp.message(CommandStart())
async def cmd_start(message: Message):
    text = RussianTexts.get("send_photo_for_analysis")
    keyboard_text = RussianButtons.get("analyze_food")
    await message.answer(f"{text}\n\nНажмите: {keyboard_text}")


@dp.message(Command("help"))
async def cmd_help(message: Message):
    await message.answer(RussianTexts.get("help_text"))


async def main():
    logging.basicConfig(level=settings.log_level)
    bot = Bot(token=settings.bot_token)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
PYEOF

# locales/ru/buttons.py
cat > "$PROJECT_ROOT/app/locales/ru/buttons.py" << 'PYEOF'
class RussianButtons:
    buttons = {
        "start": "Начать",
        "analyze_food": "📸 Анализировать еду",
        "help": "Помощь",
        "profile": "Профиль",
        "reports": "Отчеты",
        "buy_premium": "Купить премиум",
        "nutrition": "Калорийность",
        "recipe": "Рецепт",
        "new_photo": "Новое фото",
        "back": "Главная",
        "set_calorie_goal": "Установить цель по калориям",
        "calorie_plan": "План калорий",
        "buy_month_confirm": "Купить премиум на месяц",
        "buy_week_confirm": "Купить премиум на неделю",
        "enter_promo": "Ввести промокод",
        "report_day": "Отчет за день",
        "report_week": "Отчет за неделю",
        "report_month": "Отчет за месяц",
        "admin_statistics": "Статистика",
        "admin_manage_limits": "Управление лимитами",
        "admin_exit": "Выйти",
        "admin_sub_toggle_premium": "Установить режим премиум",
        "admin_sub_toggle_free": "Установить режим бесплатный",
        "admin_reset_own_limits": "Сбросить лимиты себе",
        "admin_reset_limits": "Сбросить лимиты пользователю",
        "admin_promo": "Промокод",
        "stat_week": "За неделю",
        "stat_month": "За месяц",
        "stat_all_time": "За все время",
    }

    @classmethod
    def get(cls, key: str) -> str:
        return cls.buttons.get(key, f"Кнопка:{key}")
PYEOF

# locales/ru/texts.py
cat > "$PROJECT_ROOT/app/locales/ru/texts.py" << 'PYEOF'
class RussianTexts:
    texts = {
        "send_photo_for_analysis": "📸 Отправьте фото еды для анализа",
        "help_text": "📖 Справка по использованию DishVisionBot (MVP). Здесь будет подробное описание функций позже.",
        "calories_plan_prompt": "🎯 Укажите дневной план калорий числом (от 0 до 10000).",
    }

    @classmethod
    def get(cls, key: str, **kwargs) -> str:
        text = cls.texts.get(key, f"Текст не найден: {key}")
        return text.format(**kwargs) if kwargs else text
PYEOF

# prompts/food_analysis.py — пока заглушка
cat > "$PROJECT_ROOT/app/prompts/food_analysis.py" << 'PYEOF'
# Заглушка для системных промтов анализа еды.
# Реальная логика и тексты берутся из 05_openai_prompts.md.

SYSTEM_PROMPT_NUTRITION = "TODO: добавить системный промпт для анализа калорийности."
SYSTEM_PROMPT_RECIPE = "TODO: добавить системный промпт для генерации рецепта."
PYEOF

# services/gpt_client.py — заглушка
cat > "$PROJECT_ROOT/app/services/gpt_client.py" << 'PYEOF'
import asyncio

from openai import AsyncOpenAI

from app.config import settings


class GPTClient:
    def __init__(self) -> None:
        self._client = AsyncOpenAI(api_key=settings.openai_api_key)

    async def analyze(self, prompt: str, *, user_id: str | None = None) -> str:
        # TODO: заменить на реальный вызов модели согласно 05_openai_prompts.md
        await asyncio.sleep(0.1)
        return "Заглушка ответа GPT"


gpt_client = GPTClient()
PYEOF

echo "Project skeleton created."
