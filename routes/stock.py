"""Stock tracking routes."""

from datetime import date

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from utils.auth import require_login
from utils import log_action
from models import StockItem, SessionLocal
from routes.common_list import list_items

router = APIRouter(dependencies=[Depends(require_login)])


@router.get("", response_class=HTMLResponse)
def list_stock(request: Request) -> HTMLResponse:
    """Render stock list using the common helper."""
    return list_items(
        request,
        StockItem,
        table_name="stock",
        filter_fields=StockItem.__table__.columns.keys(),
        template_name="stok.html",
        items_key="stocks",
    )


@router.post("/add")
async def add_stock(request: Request):
    """Add a stock item."""
    form = await request.form()
    db = SessionLocal()
    try:
        item = StockItem(
            urun_adi=form.get("urun_adi"),
            adet=int(form.get("adet") or 0),
            kategori=form.get("kategori"),
            marka=form.get("marka"),
            departman=form.get("departman"),
            guncelleme_tarihi=date.fromisoformat(form.get("guncelleme_tarihi")) if form.get("guncelleme_tarihi") else None,
            islem=form.get("islem"),
            tarih=date.fromisoformat(form.get("tarih")) if form.get("tarih") else None,
            ifs_no=form.get("ifs_no"),
            aciklama=form.get("aciklama"),
            islem_yapan=request.session.get("full_name", ""),
        )
        db.add(item)
        db.commit()
        log_action(
            db,
            request.session.get("username", ""),
            f"Added stock item {item.id}",
        )
    finally:
        db.close()
    return RedirectResponse("/stock", status_code=303)
