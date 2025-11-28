import asyncio
import logging
from app.db.base import init_db


from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

from app.config import settings
from app.bot.handlers import common, analysis, profile, reports, premium, admin


async def main():
    logging.basicConfig(level=settings.log_level)
    await init_db()

    bot = Bot(token=settings.bot_token)
    dp = Dispatcher(storage=MemoryStorage())

    # Регистрируем роутеры
    dp.include_router(common.router)
    dp.include_router(analysis.router)
    dp.include_router(profile.router)
    dp.include_router(reports.router)
    dp.include_router(premium.router)
    dp.include_router(admin.router)

    logging.info("Starting bot polling...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
