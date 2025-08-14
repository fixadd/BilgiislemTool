from datetime import date

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

from utils import templates, load_settings, save_settings, get_table_columns
from models import (
    SessionLocal,
    StockItem,
    PrinterInventory,
    LicenseInventory,
    HardwareInventory,
)

router = APIRouter()

# Mapping from short table identifiers used in the UI to the actual
# SQLAlchemy model classes. This allows API endpoints to operate on
# different tables in a generic manner.
MODEL_MAP = {
    "stock": StockItem,
    "printer": PrinterInventory,
    "license": LicenseInventory,
    "inventory": HardwareInventory,
}


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


@router.get("/home", response_class=HTMLResponse)
def home_page(request: Request) -> HTMLResponse:
    """Render the dashboard from the /home path."""

    context = {
        "request": request,
        "factories": {},
        "actions": [],
        "type_labels": [],
        "type_counts": [],
    }
    return templates.TemplateResponse("main.html", context)


@router.get("/inventory", response_class=HTMLResponse)
def inventory_page(request: Request) -> HTMLResponse:
    """Render the hardware inventory page."""

    context = {
        "request": request,
        "items": [],
        "columns": [],
        "column_widths": {},
        "lookups": {},
        "offset": 0,
        "page": 1,
        "total_pages": 1,
        "q": "",
        "per_page": 25,
        "table_name": "inventory",
        "filters": [],
        "count": 0,
    }
    return templates.TemplateResponse("envanter.html", context)


@router.get("/license", response_class=HTMLResponse)
def license_page(request: Request) -> HTMLResponse:
    """Render the license inventory page."""

    context = {
        "request": request,
        "licenses": [],
        "columns": [],
        "column_widths": {},
        "lookups": {},
        "offset": 0,
        "page": 1,
        "total_pages": 1,
        "q": "",
        "per_page": 25,
        "table_name": "license",
        "filters": [],
        "count": 0,
    }
    return templates.TemplateResponse("lisans.html", context)


@router.get("/accessories", response_class=HTMLResponse)
def accessories_page(request: Request) -> HTMLResponse:
    """Render the accessories tracking page."""

    return templates.TemplateResponse(
        "aksesuar.html", {"request": request, "items": []}
    )


@router.get("/requests", response_class=HTMLResponse)
def requests_page(request: Request) -> HTMLResponse:
    """Render the requests tracking page."""

    lookups = {
        "donanim_tipi": [],
        "marka": [],
        "model": [],
        "yazilim_adi": [],
        "urun_adi": [],
    }
    context = {
        "request": request,
        "groups": {},
        "lookups": lookups,
        "today": date.today().isoformat(),
    }
    return templates.TemplateResponse("talep.html", context)


@router.get("/profile", response_class=HTMLResponse)
def profile_page(request: Request) -> HTMLResponse:
    """Render a simple profile page."""

    user = {"first_name": "", "last_name": "", "email": ""}
    return templates.TemplateResponse("profile.html", {"request": request, "user": user})


@router.get("/lists", response_class=HTMLResponse)
def lists_page(request: Request) -> HTMLResponse:
    """Render the lists management page."""

    context = {
        "request": request,
        "brands": [],
        "locations": [],
        "types": [],
        "softwares": [],
        "factories": [],
        "departments": [],
        "blocks": [],
        "models": [],
        "printer_brands": [],
        "printer_models": [],
        "products": [],
    }
    return templates.TemplateResponse("listeler.html", context)


@router.get("/ping")
def ping() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/table-columns")
def table_columns(table_name: str) -> dict[str, list[str]]:
    """Return available columns for the requested table."""
    model = MODEL_MAP.get(table_name)
    if not model:
        return {"columns": []}
    cols = get_table_columns(model.__tablename__)
    return {"columns": cols}


@router.get("/column-settings")
def column_settings(table_name: str) -> dict:
    """Fetch stored column settings for a table."""
    settings = load_settings()
    return settings.get(table_name, {})


@router.post("/column-settings")
def save_column_settings(table_name: str, data: dict) -> dict[str, str]:
    """Persist column settings for a table."""
    settings = load_settings()
    settings[table_name] = data
    save_settings(settings)
    return {"status": "ok"}


@router.get("/column-values")
def column_values(table_name: str, column: str | None = None) -> dict[str, list]:
    """Return distinct values for a column to power client-side filters."""
    if not column:
        return {"values": []}
    model = MODEL_MAP.get(table_name)
    if not model or not hasattr(model, column):
        return {"values": []}
    db = SessionLocal()
    try:
        values = [row[0] for row in db.query(getattr(model, column)).distinct()]
    finally:
        db.close()
    return {"values": values}
