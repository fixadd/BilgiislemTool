"""Hardware inventory routes."""

from datetime import date

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy import or_, String
import math

from utils.auth import require_login
from utils import templates, get_table_columns, log_action
from models import HardwareInventory, SessionLocal

router = APIRouter(dependencies=[Depends(require_login)])


@router.get("", response_class=HTMLResponse)
def list_hardware(request: Request) -> HTMLResponse:
    """Render hardware inventory list."""
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
        query = db.query(HardwareInventory)

        for field, value in zip(filter_fields, filter_values):
            if field and value and hasattr(HardwareInventory, field):
                query = query.filter(getattr(HardwareInventory, field) == value)
                filters.append({"field": field, "value": value})

        if q:
            search_conditions = []
            for column in HardwareInventory.__table__.columns:
                if isinstance(column.type, String):
                    search_conditions.append(column.ilike(f"%{q}%"))
            if search_conditions:
                query = query.filter(or_(*search_conditions))

        total_count = query.count()
        total_pages = max(1, math.ceil(total_count / per_page))
        offset = (page - 1) * per_page
        items = query.offset(offset).limit(per_page).all()
    finally:
        db.close()

    context = {
        "request": request,
        "items": items,
        "columns": get_table_columns(HardwareInventory.__tablename__),
        "column_widths": {},
        "lookups": {},
        "offset": offset,
        "page": page,
        "total_pages": total_pages,
        "q": q,
        "per_page": per_page,
        "table_name": "hardware",
        "filters": filters,
        "count": total_count,
        "filter_field": filter_field,
        "filter_value": filter_value,
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
        log_action(
            db,
            request.session.get("username", ""),
            f"Added hardware item {item.id}",
        )
    finally:
        db.close()
    return RedirectResponse("/hardware", status_code=303)
