import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

from app.config import settings
from app.db.base import init_db
from app.bot.handlers import router as root_router

# роутеры
from app.bot.handlers import (
    common,
    analysis,
    profile,
    reports,
    premium,
    admin,
    main_menu,
)


async def main():
    logging.basicConfig(level=settings.log_level)
    await init_db()

    bot = Bot(token=settings.bot_token)
    dp = Dispatcher(storage=MemoryStorage())

    dp.include_router(main_menu.router)
    dp.include_router(analysis.router)
    dp.include_router(profile.router)
    dp.include_router(reports.router)
    dp.include_router(premium.router)
    dp.include_router(admin.router)
    dp.include_router(common.router)  # fallback в самом конце

    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
