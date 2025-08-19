"""Reporting and miscellaneous endpoints."""

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from sqlalchemy import case, func
from sqlalchemy.orm import Session

from utils.auth import require_login
from utils import templates
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
    actions = (
        db.query(ActivityLog)
        .order_by(ActivityLog.timestamp.desc())
        .limit(10)
        .all()
    )
    return {
        "device_summary": device_totals,
        "stock_summary": [(n, q or 0) for n, q in stock_totals],
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
    request: Request, db: Session = Depends(get_db)
) -> HTMLResponse:
    """Render simple stock status page."""

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
    return templates.TemplateResponse(
        request, "stok_durumu.html", {"summary": summary}
    )


@router.get("/ping")
def ping(request: Request):
    """Simple authenticated health check."""
    return {"status": "ok"}


__all__ = ["router"]
