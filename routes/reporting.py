"""Reporting and miscellaneous endpoints."""

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

from . import require_login
from utils import templates


router = APIRouter()


@router.get("/", response_class=HTMLResponse)
def root(request: Request) -> HTMLResponse:
    """Render the main dashboard page."""

    if redirect := require_login(request):
        return redirect
    context = {
        "factories": {},
        "actions": [],
        "type_labels": [],
        "type_counts": [],
    }
    return templates.TemplateResponse(request, "main.html", context)


@router.get("/home", response_class=HTMLResponse)
def home_page(request: Request) -> HTMLResponse:
    """Render the dashboard from the /home path."""

    if redirect := require_login(request):
        return redirect
    context = {
        "factories": {},
        "actions": [],
        "type_labels": [],
        "type_counts": [],
    }
    return templates.TemplateResponse(request, "main.html", context)


@router.get("/stock/status", response_class=HTMLResponse)
def stock_status_page(request: Request) -> HTMLResponse:
    """Render simple stock status page."""

    if redirect := require_login(request):
        return redirect
    return templates.TemplateResponse(request, "stok_durumu.html")


@router.get("/ping")
def ping(request: Request):
    """Simple authenticated health check."""

    if redirect := require_login(request):
        return redirect
    return {"status": "ok"}


__all__ = ["router"]
