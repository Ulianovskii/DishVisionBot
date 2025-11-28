import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

from app.config import settings
from app.db.base import init_db

# роутеры
from app.bot.handlers import (
    main_menu,  # ← тут живёт /start + главное меню
    common,
    analysis,
    profile,
    reports,
    premium,
    admin,
)


async def main():
    logging.basicConfig(level=settings.log_level)
    await init_db()

    bot = Bot(token=settings.bot_token)
    dp = Dispatcher(storage=MemoryStorage())

    # порядок важен: сначала старт/главное меню
    dp.include_router(main_menu.router)
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
