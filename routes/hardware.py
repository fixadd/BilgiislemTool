"""Hardware inventory routes."""

from datetime import date

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from utils.auth import require_login
from utils import templates, get_table_columns
from models import HardwareInventory, SessionLocal

router = APIRouter(dependencies=[Depends(require_login)])


@router.get("", response_class=HTMLResponse)
def list_hardware(request: Request) -> HTMLResponse:
    """Render hardware inventory list."""
    db = SessionLocal()
    try:
        items = db.query(HardwareInventory).all()
    finally:
        db.close()
    context = {
        "request": request,
        "items": items,
        "columns": get_table_columns(HardwareInventory.__tablename__),
        "column_widths": {},
        "lookups": {},
        "offset": 0,
        "page": 1,
        "total_pages": 1,
        "q": "",
        "per_page": 25,
        "table_name": "hardware",
        "filters": [],
        "count": len(items),
    }
    return templates.TemplateResponse("envanter.html", context)


@router.post("/add")
async def add_hardware(request: Request):
    """Add a hardware inventory record."""
    form = await request.form()
    db = SessionLocal()
    try:
        item = HardwareInventory(
            no=form.get("no"),
            donanim_tipi=form.get("donanim_tipi"),
            marka=form.get("marka"),
            model=form.get("model"),
            seri_no=form.get("seri_no"),
            tarih=date.fromisoformat(form.get("tarih")) if form.get("tarih") else None,
        )
        db.add(item)
        db.commit()
    finally:
        db.close()
    return RedirectResponse("/hardware", status_code=303)
