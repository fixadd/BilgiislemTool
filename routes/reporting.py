"""Reporting and miscellaneous endpoints."""

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse

from utils.auth import require_login
from utils import templates

router = APIRouter(dependencies=[Depends(require_login)])


@router.get("/", response_class=HTMLResponse)
def root(request: Request) -> HTMLResponse:
    """Render the main dashboard page."""
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
    return templates.TemplateResponse(request, "stok_durumu.html")


@router.get("/ping")
def ping(request: Request):
    """Simple authenticated health check."""
    return {"status": "ok"}


__all__ = ["router"]
