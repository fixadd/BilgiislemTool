"""Additional inventory-related page routes."""

from datetime import date

from fastapi import APIRouter, Depends, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy import or_, String
import math

from models import (
    AccessoryInventory,
    HardwareInventory,
    LicenseInventory,
    LookupItem,
    PrinterInventory,
    RequestItem,
    SessionLocal,
    StockItem,
    User,
)
from utils import get_table_columns, load_settings, save_settings, templates
from utils.auth import require_login

router = APIRouter(dependencies=[Depends(require_login)])

# Mapping used by column helper endpoints
MODEL_MAP = {
    "stock": StockItem,
    "printer": PrinterInventory,
    "license": LicenseInventory,
    "inventory": HardwareInventory,
    "accessory": AccessoryInventory,
}


@router.get("/inventory", response_class=HTMLResponse)
def inventory_page(request: Request) -> HTMLResponse:
    """Render the hardware inventory page."""
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
        "table_name": "inventory",
        "filters": filters,
        "count": total_count,
        "filter_field": filter_field,
        "filter_value": filter_value,
    }
    return templates.TemplateResponse("envanter.html", context)


@router.get("/printer", response_class=HTMLResponse)
def printer_page(request: Request) -> HTMLResponse:
    """Render the printer inventory page."""
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
        query = db.query(PrinterInventory)

        for field, value in zip(filter_fields, filter_values):
            if field and value and hasattr(PrinterInventory, field):
                query = query.filter(getattr(PrinterInventory, field) == value)
                filters.append({"field": field, "value": value})

        if q:
            search_conditions = []
            for column in PrinterInventory.__table__.columns:
                if isinstance(column.type, String):
                    search_conditions.append(column.ilike(f"%{q}%"))
            if search_conditions:
                query = query.filter(or_(*search_conditions))

        total_count = query.count()
        total_pages = max(1, math.ceil(total_count / per_page))
        offset = (page - 1) * per_page
        printers = query.offset(offset).limit(per_page).all()
    finally:
        db.close()

    context = {
        "request": request,
        "printers": printers,
        "columns": get_table_columns(PrinterInventory.__tablename__),
        "column_widths": {},
        "lookups": {},
        "offset": offset,
        "page": page,
        "total_pages": total_pages,
        "q": q,
        "per_page": per_page,
        "table_name": "printer",
        "filters": filters,
        "count": total_count,
        "filter_field": filter_field,
        "filter_value": filter_value,
    }
    return templates.TemplateResponse("yazici.html", context)


@router.get("/license", response_class=HTMLResponse)
def license_page(request: Request) -> HTMLResponse:
    """Render the software license inventory page."""
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
        query = db.query(LicenseInventory)

        for field, value in zip(filter_fields, filter_values):
            if field and value and hasattr(LicenseInventory, field):
                query = query.filter(getattr(LicenseInventory, field) == value)
                filters.append({"field": field, "value": value})

        if q:
            search_conditions = []
            for column in LicenseInventory.__table__.columns:
                if isinstance(column.type, String):
                    search_conditions.append(column.ilike(f"%{q}%"))
            if search_conditions:
                query = query.filter(or_(*search_conditions))

        total_count = query.count()
        total_pages = max(1, math.ceil(total_count / per_page))
        offset = (page - 1) * per_page
        licenses = query.offset(offset).limit(per_page).all()
    finally:
        db.close()

    context = {
        "request": request,
        "licenses": licenses,
        "columns": get_table_columns(LicenseInventory.__tablename__),
        "column_widths": {},
        "lookups": {},
        "offset": offset,
        "page": page,
        "total_pages": total_pages,
        "q": q,
        "per_page": per_page,
        "table_name": "license",
        "filters": filters,
        "count": total_count,
        "filter_field": filter_field,
        "filter_value": filter_value,
    }
    return templates.TemplateResponse("lisans.html", context)


@router.get("/accessories", response_class=HTMLResponse)
def accessories_page(request: Request) -> HTMLResponse:
    """Render the accessories inventory page."""
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
        query = db.query(AccessoryInventory)

        for field, value in zip(filter_fields, filter_values):
            if field and value and hasattr(AccessoryInventory, field):
                query = query.filter(getattr(AccessoryInventory, field) == value)
                filters.append({"field": field, "value": value})

        if q:
            search_conditions = []
            for column in AccessoryInventory.__table__.columns:
                if isinstance(column.type, String):
                    search_conditions.append(column.ilike(f"%{q}%"))
            if search_conditions:
                query = query.filter(or_(*search_conditions))

        total_count = query.count()
        total_pages = max(1, math.ceil(total_count / per_page))
        offset = (page - 1) * per_page
        accessories = query.offset(offset).limit(per_page).all()
    finally:
        db.close()

    context = {
        "request": request,
        "accessories": accessories,
        "columns": get_table_columns(AccessoryInventory.__tablename__),
        "column_widths": {},
        "lookups": {},
        "offset": offset,
        "page": page,
        "total_pages": total_pages,
        "q": q,
        "per_page": per_page,
        "table_name": "accessory",
        "filters": filters,
        "count": total_count,
        "filter_field": filter_field,
        "filter_value": filter_value,
    }
    return templates.TemplateResponse("aksesuar.html", context)


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

    db = SessionLocal()
    try:
        groups = {}
        for item in db.query(RequestItem).all():
            groups.setdefault(item.ifs_no, []).append(item)
    finally:
        db.close()

    context = {
        "groups": groups,
        "lookups": lookups,
        "today": date.today().isoformat(),
    }
    return templates.TemplateResponse(request, "talep.html", context)


@router.post("/requests/add")
async def requests_add(request: Request):
    """Add a request item."""
    form = await request.form()
    db = SessionLocal()
    try:
        kategoriler = form.getlist("kategori")
        donanim_tipleri = form.getlist("donanim_tipi")
        markalar = form.getlist("marka")
        modeller = form.getlist("model")
        yazilim_adlari = form.getlist("yazilim_adi")
        urun_adlari = form.getlist("urun_adi")
        adetler = form.getlist("adet")
        tarihler = form.getlist("tarih")
        ifs_nolar = form.getlist("ifs_no")
        aciklamalar = form.getlist("aciklama")

        for kategori, donanim_tipi, marka, model, yazilim_adi, urun_adi, adet, tarih_val, ifs_no, aciklama in zip(
            kategoriler,
            donanim_tipleri,
            markalar,
            modeller,
            yazilim_adlari,
            urun_adlari,
            adetler,
            tarihler,
            ifs_nolar,
            aciklamalar,
        ):
            item = RequestItem(
                kategori=kategori,
                donanim_tipi=donanim_tipi,
                marka=marka,
                model=model,
                yazilim_adi=yazilim_adi,
                urun_adi=urun_adi or model or "",
                adet=int(adet or 0),
                tarih=date.fromisoformat(tarih_val) if tarih_val else None,
                ifs_no=ifs_no,
                aciklama=aciklama,
                talep_acan=str(request.session.get("user_id", "")),
            )
            db.add(item)

        db.commit()
    finally:
        db.close()
    return RedirectResponse("/requests", status_code=303)


@router.get("/lists", response_class=HTMLResponse)
def lists_page(request: Request) -> HTMLResponse:
    """Render the lists management page."""
    context = {
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
    return templates.TemplateResponse(request, "listeler.html", context)


@router.post("/lists/add")
async def lists_add(request: Request, item_type: str = Form(...), name: str = Form(...)):
    """Add a lookup list item."""
    db = SessionLocal()
    try:
        db.add(LookupItem(type=item_type, name=name))
        db.commit()
    finally:
        db.close()
    return RedirectResponse("/lists", status_code=303)


@router.get("/profile", response_class=HTMLResponse)
def profile_page(request: Request) -> HTMLResponse:
    """Render a simple profile page for the current user."""
    db = SessionLocal()
    try:
        user = None
        user_id = request.session.get("user_id")
        if user_id:
            user = db.query(User).get(user_id)
    finally:
        db.close()
    return templates.TemplateResponse(request, "profile.html", {"user": user})


@router.get("/table-columns")
def table_columns(request: Request, table_name: str):
    """Return available columns for the requested table."""
    model = MODEL_MAP.get(table_name)
    if not model:
        return {"columns": []}
    cols = get_table_columns(model.__tablename__)
    return {"columns": cols}


@router.get("/column-settings")
def column_settings(request: Request, table_name: str):
    """Fetch stored column settings for a table."""
    settings = load_settings()
    return settings.get(table_name, {})


@router.post("/column-settings")
def save_column_settings(request: Request, table_name: str, data: dict):
    """Persist column settings for a table."""
    settings = load_settings()
    settings[table_name] = data
    save_settings(settings)
    return {"status": "ok"}


@router.get("/column-values")
def column_values(request: Request, table_name: str, column: str | None = None):
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


__all__ = ["router"]
