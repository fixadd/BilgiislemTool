"""Top-level API router for the application.

This package used to contain all route handlers in a single module.  To make
the codebase easier to navigate the handlers have been split into multiple
modules grouped by area of responsibility (authentication, inventory and
reporting).  Each module exposes its own ``APIRouter`` instance which is
included in the router defined here.
"""

from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse

router = APIRouter()


def require_login(request: Request) -> RedirectResponse | None:
    """Redirect unauthenticated users to the login page.

    Many endpoints require an authenticated session.  They call this helper and
    redirect the user when the session does not contain a ``"user"`` key.
    """

    if not request.session.get("user"):
        return RedirectResponse("/login", status_code=303)
    return None


# Import and register sub-routers.  The imports must happen after the helper
# above is defined so the modules can import it without causing circular
# imports.
from .authentication import router as authentication_router  # noqa: E402
from .inventory import router as inventory_router  # noqa: E402
from .reporting import router as reporting_router  # noqa: E402


# Expose all API endpoints through a single router to the FastAPI application.
router.include_router(authentication_router)
router.include_router(inventory_router)
router.include_router(reporting_router)

__all__ = ["router", "require_login"]

