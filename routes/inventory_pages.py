"""Additional inventory-related page routes."""

from datetime import date

from fastapi import APIRouter, Body, Depends, Form, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi_csrf_protect import CsrfProtect
from sqlalchemy import String, or_
from sqlalchemy.orm import Session
import math

from models import (
    AccessoryInventory,
    HardwareInventory,
    LicenseInventory,
    LookupItem,
    PrinterInventory,
    RequestItem,
    StockItem,
    User,
    get_db,
    pwd_context,
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
def inventory_page(
    request: Request,
    csrf_protect: CsrfProtect = Depends(),
    db: Session = Depends(get_db),
) -> HTMLResponse:
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
    users = db.query(User).all()
    user_list = [
        {
            "id": u.id,
            "name": (f"{u.first_name or ''} {u.last_name or ''}".strip() or u.username),
        }
        for u in users
    ]
    user_names = [u["name"] for u in user_list]
    lookups = {
        "sorumlu_personel": user_names,
        "fabrika": [i.name for i in db.query(LookupItem).filter_by(type="fabrika").all()],
        "blok": [i.name for i in db.query(LookupItem).filter_by(type="blok").all()],
        "departman": [i.name for i in db.query(LookupItem).filter_by(type="departman").all()],
        "donanim_tipi": [i.name for i in db.query(LookupItem).filter_by(type="donanim_tipi").all()],
        "marka": [i.name for i in db.query(LookupItem).filter_by(type="marka").all()],
        "model": [i.name for i in db.query(LookupItem).filter_by(type="model").all()],
        "kullanim_alani": ["kullanıcı", "üretim", "dışarı"],
    }

    token, signed = csrf_protect.generate_csrf_tokens()
    context = {
        "request": request,
        "items": items,
        "columns": get_table_columns(HardwareInventory.__tablename__),
        "column_widths": {},
        "lookups": lookups,
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
        "today": date.today().isoformat(),
        "users": user_list,
        "current_user_id": request.session.get("user_id"),
        "csrf_token": token,
    }
    response = templates.TemplateResponse(request, "envanter.html", context)
    csrf_protect.set_csrf_cookie(signed, response)
    return response


@router.get("/printer", response_class=HTMLResponse)
def printer_page(
    request: Request,
    csrf_protect: CsrfProtect = Depends(),
    db: Session = Depends(get_db),
) -> HTMLResponse:
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
    users = db.query(User).all()
    user_list = [
        {
            "id": u.id,
            "name": (f"{u.first_name or ''} {u.last_name or ''}".strip() or u.username),
        }
        for u in users
    ]
    lookups = {
        "yazici_markasi": [
            i.name
            for i in db.query(LookupItem).filter_by(type="yazici_marka").all()
        ],
        "yazici_modeli": [
            i.name
            for i in db.query(LookupItem).filter_by(type="yazici_model").all()
        ],
        "kullanim_alani": [
            i.name
            for i in db.query(LookupItem).filter_by(type="lokasyon").all()
        ],
    }

    token, signed = csrf_protect.generate_csrf_tokens()
    context = {
        "request": request,
        "printers": printers,
        "columns": get_table_columns(PrinterInventory.__tablename__),
        "column_widths": {},
        "lookups": lookups,
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
        "today": date.today().isoformat(),
        "users": user_list,
        "current_user_id": request.session.get("user_id"),
        "csrf_token": token,
    }
    response = templates.TemplateResponse(request, "yazici.html", context)
    csrf_protect.set_csrf_cookie(signed, response)
    return response


@router.get("/license", response_class=HTMLResponse)
def license_page(
    request: Request,
    csrf_protect: CsrfProtect = Depends(),
    db: Session = Depends(get_db),
) -> HTMLResponse:
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
    users = db.query(User).all()
    user_list = [
        {
            "id": u.id,
            "name": (f"{u.first_name or ''} {u.last_name or ''}".strip() or u.username),
        }
        for u in users
    ]
    user_names = [u["name"] for u in user_list]
    lookups = {
        "kullanici": user_names,
        "departman": [
            i.name
            for i in db.query(LookupItem).filter_by(type="departman").all()
        ],
        "yazilim_adi": [
            i.name for i in db.query(LookupItem).filter_by(type="yazilim").all()
        ],
    }

    token, signed = csrf_protect.generate_csrf_tokens()
    context = {
        "request": request,
        "licenses": licenses,
        "columns": get_table_columns(LicenseInventory.__tablename__),
        "column_widths": {},
        "lookups": lookups,
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
        "today": date.today().isoformat(),
        "users": user_list,
        "current_user_id": request.session.get("user_id"),
        "csrf_token": token,
    }
    response = templates.TemplateResponse(request, "lisans.html", context)
    csrf_protect.set_csrf_cookie(signed, response)
    return response


@router.get("/accessories", response_class=HTMLResponse)
def accessories_page(
    request: Request,
    csrf_protect: CsrfProtect = Depends(),
    db: Session = Depends(get_db),
) -> HTMLResponse:
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
    users = db.query(User).all()
    user_list = [
        {
            "id": u.id,
            "name": (f"{u.first_name or ''} {u.last_name or ''}".strip() or u.username),
        }
        for u in users
    ]
    user_names = [u["name"] for u in user_list]

    token, signed = csrf_protect.generate_csrf_tokens()
    context = {
        "request": request,
        "accessories": accessories,
        "columns": get_table_columns(AccessoryInventory.__tablename__),
        "column_widths": {},
        "lookups": {"kullanici": user_names},
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
        "today": date.today().isoformat(),
        "users": user_list,
        "current_user_id": request.session.get("user_id"),
        "csrf_token": token,
    }
    response = templates.TemplateResponse(request, "aksesuar.html", context)
    csrf_protect.set_csrf_cookie(signed, response)
    return response


@router.get("/requests", response_class=HTMLResponse)
def requests_page(
    request: Request,
    csrf_protect: CsrfProtect = Depends(),
    db: Session = Depends(get_db),
) -> HTMLResponse:
    """Render the requests tracking page."""
    lookups = {
        "donanim_tipi": [],
        "marka": [],
        "model": [],
        "yazilim_adi": [],
        "urun_adi": [],
    }

    groups = {}
    for item in db.query(RequestItem).all():
        groups.setdefault(item.ifs_no, []).append(item)

    token, signed = csrf_protect.generate_csrf_tokens()
    context = {
        "groups": groups,
        "lookups": lookups,
        "today": date.today().isoformat(),
        "csrf_token": token,
    }
    response = templates.TemplateResponse(request, "talep.html", context)
    csrf_protect.set_csrf_cookie(signed, response)
    return response


@router.post("/requests/add")
async def requests_add(
    request: Request,
    csrf_protect: CsrfProtect = Depends(),
    db: Session = Depends(get_db),
):
    """Add a request item."""
    form = await request.form()
    await csrf_protect.validate_csrf(request)
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
    return RedirectResponse("/requests", status_code=303)


@router.post("/requests/transfer")
async def requests_transfer(
    request: Request,
    csrf_protect: CsrfProtect = Depends(),
    db: Session = Depends(get_db),
):
    """Transfer request items into their respective inventories."""
    await csrf_protect.validate_csrf(request)
    body = await request.json()
    items = body.get("items", [])
    for data in items:
        req = db.get(RequestItem, int(data.get("id", 0)))
        if not req:
            continue
        qty = int(data.get("adet", 0) or 0)
        if qty <= 0:
            continue
        kategori = req.kategori
        if kategori == "lisans":
            for _ in range(qty):
                db.add(
                    LicenseInventory(
                        departman=data.get("departman"),
                        kullanici=data.get("kullanici"),
                        yazilim_adi=req.yazilim_adi or req.urun_adi,
                        lisans_anahtari=data.get("lisans_anahtari"),
                        mail_adresi=data.get("mail_adresi"),
                        envanter_no=data.get("envanter_no"),
                        ifs_no=req.ifs_no,
                        tarih=date.today(),
                        islem_yapan=request.session.get("full_name", ""),
                        notlar=data.get("notlar"),
                    )
                )
        elif kategori == "donanim":
            for _ in range(qty):
                db.add(
                    HardwareInventory(
                        fabrika=data.get("fabrika"),
                        blok=data.get("blok"),
                        departman=data.get("departman"),
                        donanim_tipi=req.donanim_tipi,
                        bilgisayar_adi=data.get("bilgisayar_adi"),
                        marka=req.marka,
                        model=req.model,
                        seri_no=data.get("seri_no"),
                        sorumlu_personel=data.get("sorumlu_personel"),
                        kullanim_alani=data.get("kullanim_alani"),
                        bagli_makina_no=data.get("bagli_makina_no"),
                        ifs_no=req.ifs_no,
                        tarih=date.today(),
                        islem_yapan=request.session.get("full_name", ""),
                    )
                )
        else:
            db.add(
                AccessoryInventory(
                    urun_adi=req.urun_adi,
                    adet=qty,
                    tarih=date.today(),
                    ifs_no=req.ifs_no,
                    departman=data.get("departman"),
                    kullanici="",
                    aciklama=req.aciklama,
                    islem_yapan=request.session.get("full_name", ""),
                )
            )
        if qty >= (req.adet or 0):
            db.delete(req)
        else:
            req.adet = (req.adet or 0) - qty
    db.commit()
    return JSONResponse({"status": "ok"})


@router.post("/requests/stock_transfer")
async def requests_stock_transfer(
    request: Request,
    csrf_protect: CsrfProtect = Depends(),
    db: Session = Depends(get_db),
):
    """Move request items into stock tracking."""
    await csrf_protect.validate_csrf(request)
    body = await request.json()
    items = body.get("items", [])
    for data in items:
        req = db.get(RequestItem, int(data.get("id", 0)))
        if not req:
            continue
        qty = int(data.get("adet", 0) or 0)
        if qty <= 0:
            continue
        db.add(
            StockItem(
                urun_adi=req.urun_adi,
                kategori=req.kategori,
                marka=req.marka,
                adet=qty,
                departman=None,
                guncelleme_tarihi=date.today(),
                islem="giris",
                tarih=date.today(),
                ifs_no=req.ifs_no,
                aciklama=req.aciklama,
                islem_yapan=request.session.get("full_name", ""),
            )
        )
        if qty >= (req.adet or 0):
            db.delete(req)
        else:
            req.adet = (req.adet or 0) - qty
    db.commit()
    return JSONResponse({"status": "ok"})


@router.post("/requests/delete")
async def requests_delete(
    request: Request,
    csrf_protect: CsrfProtect = Depends(),
    db: Session = Depends(get_db),
):
    """Delete selected request records."""
    await csrf_protect.validate_csrf(request)
    body = await request.json()
    ids = [int(i) for i in body.get("ids", [])]
    if ids:
        db.query(RequestItem).filter(RequestItem.id.in_(ids)).delete(
            synchronize_session=False
        )
        db.commit()
    return JSONResponse({"status": "ok"})


@router.get("/lists", response_class=HTMLResponse)
def lists_page(
    request: Request,
    csrf_protect: CsrfProtect = Depends(),
    db: Session = Depends(get_db),
) -> HTMLResponse:
    """Render the lists management page."""
    context = {
        "brands": db.query(LookupItem).filter_by(type="marka").all(),
        "locations": db.query(LookupItem).filter_by(type="lokasyon").all(),
        "types": db.query(LookupItem).filter_by(type="donanim_tipi").all(),
        "softwares": db.query(LookupItem).filter_by(type="yazilim").all(),
        "factories": db.query(LookupItem).filter_by(type="fabrika").all(),
        "departments": db.query(LookupItem).filter_by(type="departman").all(),
        "blocks": db.query(LookupItem).filter_by(type="blok").all(),
        "models": db.query(LookupItem).filter_by(type="model").all(),
        "printer_brands": db.query(LookupItem).filter_by(type="yazici_marka").all(),
        "printer_models": db.query(LookupItem).filter_by(type="yazici_model").all(),
        "products": db.query(LookupItem).filter_by(type="urun").all(),
    }
    token, signed = csrf_protect.generate_csrf_tokens()
    context["csrf_token"] = token
    response = templates.TemplateResponse(request, "listeler.html", context)
    csrf_protect.set_csrf_cookie(signed, response)
    return response


@router.post("/lists/add")
async def lists_add(
    request: Request,
    csrf_protect: CsrfProtect = Depends(),
    item_type: str = Form(...),
    name: str = Form(...),
    db: Session = Depends(get_db),
):
    """Add a lookup list item."""
    await csrf_protect.validate_csrf(request)
    db.add(LookupItem(type=item_type, name=name))
    db.commit()
    return RedirectResponse("/lists", status_code=303)


@router.post("/lists/delete")
async def lists_delete(
    request: Request,
    csrf_protect: CsrfProtect = Depends(),
    item_id: int = Form(...),
    force: int = Form(0),
    db: Session = Depends(get_db),
):
    """Delete a lookup list item, optionally forcing if it's in use."""
    await csrf_protect.validate_csrf(request)
    item = db.get(LookupItem, item_id)
    if not item:
        return JSONResponse({"status": "not_found"}, status_code=404)

    def item_in_use() -> bool:
        checks = {
            "marka": [HardwareInventory.marka, StockItem.marka],
            "model": [HardwareInventory.model],
            "donanim_tipi": [HardwareInventory.donanim_tipi],
            "fabrika": [HardwareInventory.fabrika],
            "departman": [HardwareInventory.departman, LicenseInventory.departman],
            "blok": [HardwareInventory.blok],
            "lokasyon": [StockItem.departman],
            "yazilim": [LicenseInventory.yazilim_adi],
            "yazici_marka": [PrinterInventory.yazici_markasi],
            "yazici_model": [PrinterInventory.yazici_modeli],
            "urun": [StockItem.urun_adi],
        }
        columns = checks.get(item.type, [])
        for col in columns:
            model = col.class_
            if db.query(model).filter(col == item.name).first():
                return True
        return False

    if not force and item_in_use():
        return JSONResponse({"status": "used"})

    db.delete(item)
    db.commit()
    return JSONResponse({"status": "deleted"})


@router.get("/profile", response_class=HTMLResponse)
def profile_page(
    request: Request, db: Session = Depends(get_db)
) -> HTMLResponse:
    """Render a simple profile page for the current user."""
    user = None
    user_id = request.session.get("user_id")
    if user_id:
        user = db.get(User, user_id)
    return templates.TemplateResponse(request, "profile.html", {"user": user})


@router.get("/change-password", response_class=HTMLResponse)
def change_password_form(
    request: Request, csrf_protect: CsrfProtect = Depends()
) -> HTMLResponse:
    """Display the password change form."""
    token, signed = csrf_protect.generate_csrf_tokens()
    response = templates.TemplateResponse(
        request, "change_password.html", {"csrf_token": token}
    )
    csrf_protect.set_csrf_cookie(signed, response)
    return response


@router.post("/change-password")
async def change_password(
    request: Request,
    csrf_protect: CsrfProtect = Depends(),
    old_password: str = Form(...),
    new_password: str = Form(...),
    confirm_password: str = Form(...),
    db: Session = Depends(get_db),
):
    """Allow the current user to update their password."""
    await csrf_protect.validate_csrf(request)
    if new_password != confirm_password:
        return templates.TemplateResponse(
            request,
            "change_password.html",
            {"error": "Yeni şifreler uyuşmuyor"},
            status_code=400,
        )

    user_id = request.session.get("user_id")
    user = db.get(User, user_id) if user_id else None
    if not user or not pwd_context.verify(old_password, user.password):
        return templates.TemplateResponse(
            request,
            "change_password.html",
            {"error": "Mevcut şifre yanlış"},
            status_code=400,
        )

    user.password = pwd_context.hash(new_password)
    user.must_change_password = False
    db.commit()

    return RedirectResponse("/profile", status_code=303)


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
async def save_column_settings(
    request: Request,
    table_name: str,
    data: dict = Body(...),
    csrf_protect: CsrfProtect = Depends(),
):
    """Persist column settings for a table."""
    await csrf_protect.validate_csrf(request)
    settings = load_settings()
    data.pop("csrf_token", None)
    settings[table_name] = data
    save_settings(settings)
    return {"status": "ok"}


@router.get("/column-values")
def column_values(
    request: Request, table_name: str, column: str | None = None, db: Session = Depends(get_db)
):
    """Return distinct values for a column to power client-side filters."""
    if not column:
        return {"values": []}
    model = MODEL_MAP.get(table_name)
    if not model or not hasattr(model, column):
        return {"values": []}
    values = [row[0] for row in db.query(getattr(model, column)).distinct()]
    return {"values": values}


__all__ = ["router"]
