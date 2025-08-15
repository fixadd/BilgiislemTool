"""API router assembly for the application."""

from fastapi import APIRouter

from .auth import router as auth_router
from .hardware import router as hardware_router
from .stock import router as stock_router
from .reporting import router as reporting_router
from .inventory_logs import router as inventory_logs_router
from .reports import router as reports_router
from .admin import router as admin_router
from .inventory_pages import router as inventory_pages_router
from .inventory import router as inventory_router
from .connections import router as connections_router
from .trash import router as trash_router

router = APIRouter()
router.include_router(auth_router)
router.include_router(hardware_router, prefix="/hardware")
router.include_router(stock_router, prefix="/stock")
router.include_router(reporting_router)
router.include_router(admin_router)
router.include_router(inventory_pages_router)
router.include_router(inventory_router)
router.include_router(connections_router)
router.include_router(inventory_logs_router)
router.include_router(reports_router)
router.include_router(trash_router)

__all__ = ["router"]
