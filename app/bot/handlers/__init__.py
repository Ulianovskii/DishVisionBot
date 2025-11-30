from aiogram import Router

from . import common, analysis, profile, reports, premium, admin, main_menu

router = Router(name="root")

router.include_router(common.router)
router.include_router(analysis.router)
router.include_router(profile.router)
router.include_router(reports.router)
router.include_router(premium.router)
router.include_router(admin.router)
router.include_router(main_menu.router)

__all__ = ["router"]
