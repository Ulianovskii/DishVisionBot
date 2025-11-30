# app/bot/handlers/reports.py

from aiogram import Router, F
from aiogram.types import Message

from app.bot.keyboards import reports_menu_kb
from app.locales.ru.buttons import RussianButtons as B
from app.locales.ru.texts import RussianTexts as T

router = Router()


@router.message(F.text == B.get("reports"))
async def open_reports(message: Message):
    await message.answer(
        T.get("reports_placeholder"),
        reply_markup=reports_menu_kb(),
    )


@router.message(F.text == B.get("report_day"))
async def report_day_stub(message: Message):
    await message.answer(T.get("report_day_placeholder"))


@router.message(F.text == B.get("report_week"))
async def report_week_stub(message: Message):
    await message.answer(T.get("report_week_placeholder"))


@router.message(F.text == B.get("report_month"))
async def report_month_stub(message: Message):
    await message.answer(T.get("report_month_placeholder"))
