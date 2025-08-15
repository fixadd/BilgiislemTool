"""Stock tracking routes."""

from datetime import date

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy import or_, String
import math

from utils.auth import require_login
from utils import templates, get_table_columns, log_action
from models import StockItem, SessionLocal

router = APIRouter(dependencies=[Depends(require_login)])


@router.get("", response_class=HTMLResponse)
def list_stock(request: Request) -> HTMLResponse:
    """Render stock list."""
    params = request.query_params
    q = params.get("q", "")
    filter_fields = params.getlist("filter_field")
    filter_values = params.getlist("filter_value")
    filter_field = filter_fields[0] if filter_fields else None
    filter_value = filter_values[0] if filter_values else None
    page = int(params.get("page", 1))
    per_page = int(params.get("per_page", 25))

    filters = []
    db = SessionLocal()
    try:
        query = db.query(StockItem)

        for field, value in zip(filter_fields, filter_values):
            if field and value and hasattr(StockItem, field):
                query = query.filter(getattr(StockItem, field) == value)
                filters.append({"field": field, "value": value})

        if q:
            search_conditions = []
            for column in StockItem.__table__.columns:
                if isinstance(column.type, String):
                    search_conditions.append(column.ilike(f"%{q}%"))
            if search_conditions:
                query = query.filter(or_(*search_conditions))

        total_count = query.count()
        total_pages = max(1, math.ceil(total_count / per_page))
        offset = (page - 1) * per_page
        stocks = query.offset(offset).limit(per_page).all()
    finally:
        db.close()

    context = {
        "request": request,
        "stocks": stocks,
        "columns": get_table_columns(StockItem.__tablename__),
        "column_widths": {},
        "lookups": {},
        "offset": offset,
        "page": page,
        "total_pages": total_pages,
        "q": q,
        "per_page": per_page,
        "table_name": "stock",
        "filters": filters,
        "count": total_count,
        "filter_field": filter_field,
        "filter_value": filter_value,
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
