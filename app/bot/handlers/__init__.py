# app/bot/handlers/__init__.py

from aiogram import Router

from . import (
    common,
    analysis,
    profile,
    premium,
    admin,
    payments,
    main_menu,
    # reports,  # 👈 временно отключили модуль отчётов
)

router = Router(name="root")

# Порядок важен: сначала более "узкие" вещи (платежи),
# потом общие меню с fallback-хендлерами.
router.include_router(common.router)
router.include_router(analysis.router)
router.include_router(profile.router)
router.include_router(premium.router)
router.include_router(admin.router)
router.include_router(payments.router)
router.include_router(main_menu.router)
# router.include_router(reports.router)  # 👈 тоже отключили
