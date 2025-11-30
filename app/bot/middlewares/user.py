# app/bot/middlewares/user.py

from typing import Any, Awaitable, Callable, Dict

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from app.services.user_service import get_or_create_user


class UserMiddleware(BaseMiddleware):
    """
    На каждом апдейте:
    - гарантирует, что пользователь есть в БД;
    - кладёт объект User в data["db_user"];
    - кладёт user_id в FSM (state.data["user_id"]).
    """

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        tg_user = None

        if isinstance(event, Message):
            tg_user = event.from_user
        elif isinstance(event, CallbackQuery):
            tg_user = event.from_user

        if tg_user is not None:
            user = await get_or_create_user(telegram_id=tg_user.id)
            # кладём и под старым ключом, и под универсальным
            data["db_user"] = user
            data["user"] = user

            state: FSMContext | None = data.get("state")
            if state is not None:
                await state.update_data(user_id=user.id)

        return await handler(event, data)
