"""Stock tracking routes."""

from datetime import date

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from utils.auth import require_login
from utils import templates, get_table_columns
from models import StockItem, SessionLocal

router = APIRouter(dependencies=[Depends(require_login)])


@router.get("", response_class=HTMLResponse)
def list_stock(request: Request) -> HTMLResponse:
    """Render stock list."""
    db = SessionLocal()
    try:
        stocks = db.query(StockItem).all()
    finally:
        db.close()
    context = {
        "request": request,
        "stocks": stocks,
        "columns": get_table_columns(StockItem.__tablename__),
        "column_widths": {},
        "lookups": {},
        "offset": 0,
        "page": 1,
        "total_pages": 1,
        "q": "",
        "per_page": 25,
        "table_name": "stock",
        "filters": [],
        "count": len(stocks),
    }
    return templates.TemplateResponse("stok.html", context)


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
            islem_yapan=form.get("islem_yapan"),
        )
        db.add(item)
        db.commit()
    finally:
        db.close()
    return RedirectResponse("/stock", status_code=303)
