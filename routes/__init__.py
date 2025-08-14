"""API router assembly for the application."""

from fastapi import APIRouter

from .auth import router as auth_router
from .inventory import router as inventory_router
from .reporting import router as reporting_router
from .admin import router as admin_router

router = APIRouter()
router.include_router(auth_router)
router.include_router(inventory_router)
router.include_router(reporting_router)
router.include_router(admin_router)

__all__ = ["router"]
