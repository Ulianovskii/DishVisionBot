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
