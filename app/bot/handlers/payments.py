# app/bot/handlers/payments.py

from aiogram import Router, F
from aiogram.types import Message, LabeledPrice, PreCheckoutQuery, CallbackQuery
from aiogram.fsm.context import FSMContext

from app.locales.ru.texts import RussianTexts as T
from app.locales.ru.buttons import RussianButtons as B
from app.services.user_service import get_or_create_user
from app.config_limits import STARS_PREMIUM_WEEK, STARS_PREMIUM_MONTH, PRICE_PER_ANALYSIS
from app.db.base import AsyncSessionLocal
from app.db import models


router = Router(name="payments")


# ------- 5 анализов (helper) -------
async def _send_analyses_invoice(chat_id: int, bot):
    """
    Отправляет invoice на покупку пакета анализов (5 шт. по настройкам).
    """
    number = PRICE_PER_ANALYSIS["number_of_analyses"]
    price = PRICE_PER_ANALYSIS["price"]

    prices = [
        LabeledPrice(
            label=f"{number} анализов",
            amount=price,  # для Stars amount = количество звёзд
        )
    ]

    await bot.send_invoice(
        chat_id=chat_id,
        title=f"Пакет из {number} анализов",
        description=f"Дополнительные {number} анализов еды",
        payload="analyses_pack",
        currency="XTR",
        prices=prices,
        provider_token="",  # для Stars — пустая строка
    )


# ------- PREMIUM WEEK -------
@router.message(F.text == B.get("buy_week_confirm"))
async def on_buy_premium_week(message: Message, state: FSMContext):
    prices = [LabeledPrice(label="Premium 7 days", amount=STARS_PREMIUM_WEEK)]
    await message.bot.send_invoice(
        chat_id=message.chat.id,
        title="Премиум на неделю",
        description="Премиум-доступ на 7 дней",
        payload="premium_week",
        currency="XTR",
        prices=prices,
        provider_token="",   # Stars всегда без токена
    )


# ------- PREMIUM MONTH -------
@router.message(F.text == B.get("buy_month_confirm"))
async def on_buy_premium_month(message: Message, state: FSMContext):
    prices = [LabeledPrice(label="Premium 30 days", amount=STARS_PREMIUM_MONTH)]
    await message.bot.send_invoice(
        chat_id=message.chat.id,
        title="Премиум на месяц",
        description="Премиум-доступ на 30 дней",
        payload="premium_month",
        currency="XTR",
        prices=prices,
        provider_token="",
    )


# ------- Покупка пакета анализов (из инлайн-кнопки) -------
@router.callback_query(F.data == "buy_analyses_pack")
async def on_buy_analyses_pack(callback: CallbackQuery):
    await _send_analyses_invoice(
        chat_id=callback.message.chat.id,
        bot=callback.message.bot,
    )
    # Закрываем "часики" на кнопке
    await callback.answer()


# ------- Покупка пакета анализов (из профиля) -------
@router.message(F.text == B.get("buy_analyses"))
async def on_buy_analyses_from_profile(message: Message, state: FSMContext):
    """
    Обработка кнопки '⭐ Купить 5 анализов' из профиля.
    """
    await _send_analyses_invoice(
        chat_id=message.chat.id,
        bot=message.bot,
    )


# ------- CALLBACK НА ПРЕДОПЛАТУ -------
@router.pre_checkout_query()
async def process_pre_checkout_query(query: PreCheckoutQuery):
    await query.answer(ok=True)


# ------- УСПЕШНАЯ ОПЛАТА -------
@router.message(F.successful_payment)
async def on_successful_payment(message: Message):
    payload = message.successful_payment.invoice_payload
    telegram_id = message.from_user.id

    user = await get_or_create_user(telegram_id)

    async with AsyncSessionLocal() as session:
        if payload == "premium_week":
            user.is_premium = True
            user.premium_until = None  # TODO: потом сделаем нормальную дату
            text = "🎉 Оплата прошла успешно! Премиум на неделю активирован."
        elif payload == "premium_month":
            user.is_premium = True
            user.premium_until = None
            text = "🎉 Оплата прошла успешно! Премиум на месяц активирован."
        elif payload == "analyses_pack":
            # начисляем платные анализы
            user.paid_photos_balance = (user.paid_photos_balance or 0) + PRICE_PER_ANALYSIS["number_of_analyses"]
            text = f"🎉 Оплата прошла! Вам начислено {PRICE_PER_ANALYSIS['number_of_analyses']} дополнительных анализов."
        else:
            text = "✅ Оплата прошла."

        await session.merge(user)
        await session.commit()

    await message.answer(text)
