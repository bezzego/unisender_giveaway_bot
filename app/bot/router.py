from aiogram import Router

from app.bot.admin import router as admin_router
from app.bot.handlers import router as handlers_router

router = Router()
router.include_router(admin_router)
router.include_router(handlers_router)
