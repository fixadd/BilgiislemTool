from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

from utils import templates

router = APIRouter()


@router.get("/", response_class=HTMLResponse)
def root(request: Request) -> HTMLResponse:
    """Render the main dashboard page.

    The template expects a number of context variables. Provide
    sensible defaults so the page can render even when the database
    is empty or not yet configured.
    """

    context = {
        "request": request,
        "factories": {},
        "actions": [],
        "type_labels": [],
        "type_counts": [],
    }
    return templates.TemplateResponse("main.html", context)


@router.get("/login", response_class=HTMLResponse)
def login_page(request: Request, error: str | None = None) -> HTMLResponse:
    """Render the login page."""

    return templates.TemplateResponse("login.html", {"request": request, "error": error})


@router.get("/stock", response_class=HTMLResponse)
def stock_page(request: Request) -> HTMLResponse:
    """Render the stock tracking page with empty defaults."""

    context = {
        "request": request,
        "stocks": [],
        "columns": [],
        "column_widths": {},
        "lookups": {},
        "offset": 0,
        "page": 1,
        "total_pages": 1,
        "q": "",
        "per_page": 25,
        "table_name": "stock",
        "filters": [],
    }
    return templates.TemplateResponse("stok.html", context)


@router.get("/printer", response_class=HTMLResponse)
def printer_page(request: Request) -> HTMLResponse:
    """Render the printer inventory page with empty defaults."""

    context = {
        "request": request,
        "printers": [],
        "columns": [],
        "column_widths": {},
        "offset": 0,
        "page": 1,
        "total_pages": 1,
        "q": "",
        "per_page": 25,
        "table_name": "printer",
        "filters": [],
    }
    return templates.TemplateResponse("yazici.html", context)


@router.get("/ping")
def ping() -> dict[str, str]:
    return {"status": "ok"}
