import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

from app.config import settings
from app.db.base import init_db
from app.bot.handlers import router as root_router

from app.bot.middlewares.user import UserMiddleware



async def main():
    logging.basicConfig(level=settings.log_level)
    await init_db()

    bot = Bot(token=settings.bot_token)
    dp = Dispatcher(storage=MemoryStorage())

    # ✨ вот здесь вешаем middleware
    dp.message.middleware(UserMiddleware())
    dp.callback_query.middleware(UserMiddleware())

    from app.bot.handlers import router as root_router
    dp.include_router(root_router)

    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
