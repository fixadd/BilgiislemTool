"""Hardware inventory routes."""

from datetime import date

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from utils.auth import require_login
from utils import log_action
from models import HardwareInventory, SessionLocal
from routes.common_list import list_items

router = APIRouter(dependencies=[Depends(require_login)])


@router.get("", response_class=HTMLResponse)
def list_hardware(request: Request) -> HTMLResponse:
    """Render hardware inventory list using the common helper."""
    return list_items(
        request,
        HardwareInventory,
        table_name="hardware",
        filter_fields=HardwareInventory.__table__.columns.keys(),
        template_name="envanter.html",
        items_key="items",
    )


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
        log_action(
            db,
            request.session.get("username", ""),
            f"Added hardware item {item.id}",
        )
    finally:
        db.close()
    return RedirectResponse("/hardware", status_code=303)
