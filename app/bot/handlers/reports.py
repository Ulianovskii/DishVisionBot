from aiogram import Router, F
from aiogram.types import Message

from app.bot.keyboards import reports_menu_kb
from app.locales.ru.buttons import RussianButtons as B

router = Router()


@router.message(F.text == B.get("reports"))
async def open_reports(message: Message):
    await message.answer(
        "📊 Раздел отчётов.\n"
        "Здесь позже будут отчёты за день/неделю/месяц.",
        reply_markup=reports_menu_kb(),
    )


@router.message(F.text == B.get("report_day"))
async def report_day_stub(message: Message):
    await message.answer("🗓 Отчёт за день (заглушка).")


@router.message(F.text == B.get("report_week"))
async def report_week_stub(message: Message):
    await message.answer("📅 Отчёт за неделю (заглушка).")


@router.message(F.text == B.get("report_month"))
async def report_month_stub(message: Message):
    await message.answer("📆 Отчёт за месяц (заглушка).")
