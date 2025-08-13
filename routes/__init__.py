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


@router.get("/column-settings")
def get_column_settings(table_name: str) -> dict:
    """Return saved column settings for a table.

    The real application would fetch the settings from persistent
    storage. For now, return an empty configuration so the front-end
    has something to work with instead of a 404 response.
    """

    return {}


@router.post("/column-settings")
def save_column_settings(table_name: str, settings: dict) -> dict:
    """Persist column settings for a table.

    This stub simply echoes the provided settings back to the client.
    """

    return settings


@router.get("/table-columns")
def get_table_columns(table_name: str) -> dict:
    """Return the available columns for a table.

    Provide an empty list so pages can initialise without database
    access.
    """

    return {"columns": []}


@router.get("/column-values")
def get_column_values(table_name: str, column: str) -> list:
    """Return distinct values for a given column.

    The front-end uses this for building filter dropdowns. Return an
    empty list to avoid 404 errors when no data is present.
    """

    return []


@router.get("/ping")
def ping() -> dict[str, str]:
    return {"status": "ok"}
