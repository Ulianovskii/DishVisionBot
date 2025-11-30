# app/bot/handlers/__init__.py

from aiogram import Router

from . import (
    common,
    analysis,
    profile,
    premium,
    admin,
    main_menu,
    payments,
    # reports,  # 👈 временно отключили модуль отчётов
)

router = Router(name="root")

router.include_router(common.router)
router.include_router(analysis.router)
router.include_router(profile.router)
router.include_router(premium.router)
router.include_router(admin.router)
router.include_router(main_menu.router)
router.include_router(payments.router)
# router.include_router(reports.router)  # 👈 тоже отключили
