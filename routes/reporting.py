"""Reporting and miscellaneous endpoints."""

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi_csrf_protect import CsrfProtect
from sqlalchemy import case, func
from sqlalchemy.orm import Session

from utils.auth import require_login
from utils import templates, load_home_stock, save_home_stock
from models import ActivityLog, HardwareInventory, StockItem, get_db

router = APIRouter(dependencies=[Depends(require_login)])


def _main_context(db: Session) -> dict:
    """Gather summary info for the main dashboard."""
    device_totals = (
        db.query(HardwareInventory.donanim_tipi, func.count())
        .group_by(HardwareInventory.donanim_tipi)
        .all()
    )
    stock_totals = (
        db.query(
            StockItem.urun_adi,
            func.sum(
                case((StockItem.islem == "giris", StockItem.adet), else_=-StockItem.adet)
            ).label("net_adet"),
        )
        .group_by(StockItem.urun_adi)
        .all()
    )
    selected = set(load_home_stock())
    stock_summary = [
        (name, qty or 0)
        for name, qty in stock_totals
        if not selected or name in selected
    ]
    actions = (
        db.query(ActivityLog)
        .order_by(ActivityLog.timestamp.desc())
        .limit(10)
        .all()
    )
    return {
        "device_summary": device_totals,
        "stock_summary": stock_summary,
        "actions": actions,
    }


@router.get("/", response_class=HTMLResponse)
def root(request: Request, db: Session = Depends(get_db)) -> HTMLResponse:
    """Render the main dashboard page."""
    return templates.TemplateResponse(request, "main.html", _main_context(db))


@router.get("/home", response_class=HTMLResponse)
def home_page(request: Request, db: Session = Depends(get_db)) -> HTMLResponse:
    """Render the dashboard from the /home path."""
    return templates.TemplateResponse(request, "main.html", _main_context(db))


@router.get("/stock/status", response_class=HTMLResponse)
def stock_status_page(
    request: Request,
    db: Session = Depends(get_db),
    csrf_protect: CsrfProtect = Depends(),
) -> HTMLResponse:
    """Render stock status page with dashboard selection controls."""

    totals = (
        db.query(
            StockItem.urun_adi,
            func.sum(
                case(
                    (StockItem.islem == "giris", StockItem.adet),
                    else_=-StockItem.adet,
                )
            ).label("net_adet"),
        )
        .group_by(StockItem.urun_adi)
        .all()
    )

    summary = [(name, qty or 0) for name, qty in totals]
    selected = load_home_stock()
    token, signed = csrf_protect.generate_csrf_tokens()
    context = {"summary": summary, "selected": selected, "csrf_token": token}
    response = templates.TemplateResponse(request, "stok_durumu.html", context)
    csrf_protect.set_csrf_cookie(signed, response)
    return response


@router.post("/stock/status")
async def save_stock_status(
    request: Request,
    csrf_protect: CsrfProtect = Depends(),
):
    """Persist selected stock items for dashboard display."""
    await csrf_protect.validate_csrf(request)
    form = await request.form()
    selected = form.getlist("selected")
    save_home_stock(selected)
    return RedirectResponse("/stock/status", status_code=303)


@router.get("/ping")
def ping(request: Request):
    """Simple authenticated health check."""
    return {"status": "ok"}


__all__ = ["router"]
