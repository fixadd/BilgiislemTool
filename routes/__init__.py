from datetime import date

from fastapi import APIRouter, Request, Form, UploadFile, File
from fastapi.responses import HTMLResponse, RedirectResponse

from utils import templates, load_settings, save_settings, get_table_columns
from models import (
    SessionLocal,
    StockItem,
    PrinterInventory,
    LicenseInventory,
    HardwareInventory,
    RequestItem,
    LookupItem,
    User,
    pwd_context,
)

router = APIRouter()

# Mapping from short table identifiers used in the UI to the actual
# SQLAlchemy model classes. This allows API endpoints to operate on
# different tables in a generic manner.
MODEL_MAP = {
    "stock": StockItem,
    "printer": PrinterInventory,
    "license": LicenseInventory,
    "inventory": HardwareInventory,
}


@router.get("/", response_class=HTMLResponse)
def root(request: Request) -> HTMLResponse:
    """Render the main dashboard page.

    The template expects a number of context variables. Provide
    sensible defaults so the page can render even when the database
    is empty or not yet configured.
    """

    context = {
        "request": request,
        "factories": {},
        "actions": [],
        "type_labels": [],
        "type_counts": [],
    }
    return templates.TemplateResponse("main.html", context)


@router.get("/login", response_class=HTMLResponse)
def login_page(request: Request, error: str | None = None) -> HTMLResponse:
    """Render the login page."""

    return templates.TemplateResponse("login.html", {"request": request, "error": error})


@router.post("/login")
def login(request: Request, username: str = Form(...), password: str = Form(...)):
    """Basic form-based login."""

    db = SessionLocal()
    try:
        user = db.query(User).filter(User.username == username).first()
        if user and pwd_context.verify(password, user.password):
            request.session["user"] = user.username
            return RedirectResponse("/", status_code=303)
    finally:
        db.close()
    return templates.TemplateResponse(
        "login.html",
        {"request": request, "error": "Invalid credentials"},
        status_code=401,
    )


@router.get("/stock", response_class=HTMLResponse)
def stock_page(request: Request) -> HTMLResponse:
    """Render the stock tracking page with empty defaults."""

    context = {
        "request": request,
        "stocks": [],
        "columns": [],
        "column_widths": {},
        "lookups": {},
        "offset": 0,
        "page": 1,
        "total_pages": 1,
        "q": "",
        "per_page": 25,
        "table_name": "stock",
        "filters": [],
    }
    return templates.TemplateResponse("stok.html", context)


@router.get("/stock/status", response_class=HTMLResponse)
def stock_status_page(request: Request) -> HTMLResponse:
    """Render simple stock status page."""

    return templates.TemplateResponse("stok_durumu.html", {"request": request})


@router.post("/stock/add")
async def stock_add(request: Request):
    """Create or update a stock item from form data."""

    form = await request.form()
    db = SessionLocal()
    try:
        stock_id = form.get("stock_id")
        if stock_id:
            item = db.query(StockItem).get(int(stock_id))
            if item:
                for field in [
                    "urun_adi",
                    "kategori",
                    "marka",
                    "adet",
                    "departman",
                    "guncelleme_tarihi",
                    "islem",
                    "tarih",
                    "ifs_no",
                    "aciklama",
                    "islem_yapan",
                ]:
                    if field in form:
                        value = form.get(field)
                        if field in {"adet"}:
                            value = int(value) if value else None
                        elif field in {"guncelleme_tarihi", "tarih"}:
                            value = date.fromisoformat(value) if value else None
                        setattr(item, field, value)
        else:
            item = StockItem(
                urun_adi=form.get("urun_adi"),
                kategori=form.get("kategori"),
                marka=form.get("marka"),
                adet=int(form.get("adet") or 0),
                departman=form.get("departman"),
                guncelleme_tarihi=
                    date.fromisoformat(form.get("guncelleme_tarihi"))
                    if form.get("guncelleme_tarihi")
                    else None,
                islem=form.get("islem"),
                tarih=
                    date.fromisoformat(form.get("tarih"))
                    if form.get("tarih")
                    else None,
                ifs_no=form.get("ifs_no"),
                aciklama=form.get("aciklama"),
                islem_yapan=form.get("islem_yapan"),
            )
            db.add(item)
        db.commit()
    finally:
        db.close()
    return RedirectResponse("/stock", status_code=303)


@router.get("/printer", response_class=HTMLResponse)
def printer_page(request: Request) -> HTMLResponse:
    """Render the printer inventory page with empty defaults."""

    context = {
        "request": request,
        "printers": [],
        "columns": [],
        "column_widths": {},
        "offset": 0,
        "page": 1,
        "total_pages": 1,
        "q": "",
        "per_page": 25,
        "table_name": "printer",
        "filters": [],
    } 
    return templates.TemplateResponse("yazici.html", context)


@router.post("/printer/add")
async def printer_add(request: Request):
    """Create or update a printer inventory item."""

    form = await request.form()
    db = SessionLocal()
    try:
        printer_id = form.get("printer_id")
        if printer_id:
            item = db.query(PrinterInventory).get(int(printer_id))
            if item:
                for field in [
                    "yazici_markasi",
                    "yazici_modeli",
                    "kullanim_alani",
                    "ip_adresi",
                    "mac",
                    "hostname",
                    "tarih",
                    "islem_yapan",
                    "notlar",
                ]:
                    if field in form:
                        value = form.get(field)
                        if field == "tarih":
                            value = date.fromisoformat(value) if value else None
                        setattr(item, field, value)
        else:
            item = PrinterInventory(
                yazici_markasi=form.get("yazici_markasi"),
                yazici_modeli=form.get("yazici_modeli"),
                kullanim_alani=form.get("kullanim_alani"),
                ip_adresi=form.get("ip_adresi"),
                mac=form.get("mac"),
                hostname=form.get("hostname"),
                tarih=
                    date.fromisoformat(form.get("tarih"))
                    if form.get("tarih")
                    else None,
                islem_yapan=form.get("islem_yapan"),
                notlar=form.get("notlar"),
            )
            db.add(item)
        db.commit()
    finally:
        db.close()
    return RedirectResponse("/printer", status_code=303)


@router.post("/printer/upload")
async def printer_upload(excel_file: UploadFile = File(...)):
    """Accept a printer inventory Excel upload (currently discarded)."""

    await excel_file.read()
    return RedirectResponse("/printer", status_code=303)


@router.get("/home", response_class=HTMLResponse)
def home_page(request: Request) -> HTMLResponse:
    """Render the dashboard from the /home path."""

    context = {
        "request": request,
        "factories": {},
        "actions": [],
        "type_labels": [],
        "type_counts": [],
    }
    return templates.TemplateResponse("main.html", context)


@router.get("/inventory", response_class=HTMLResponse)
def inventory_page(request: Request) -> HTMLResponse:
    """Render the hardware inventory page."""

    context = {
        "request": request,
        "items": [],
        "columns": [],
        "column_widths": {},
        "lookups": {},
        "offset": 0,
        "page": 1,
        "total_pages": 1,
        "q": "",
        "per_page": 25,
        "table_name": "inventory",
        "filters": [],
        "count": 0,
    }
    return templates.TemplateResponse("envanter.html", context)


@router.post("/inventory/add")
async def inventory_add(request: Request):
    """Create or update a hardware inventory record."""

    form = await request.form()
    db = SessionLocal()
    try:
        item_id = form.get("item_id")
        if item_id:
            item = db.query(HardwareInventory).get(int(item_id))
            if item:
                for field in [
                    "no",
                    "fabrika",
                    "blok",
                    "departman",
                    "donanim_tipi",
                    "bilgisayar_adi",
                    "marka",
                    "model",
                    "seri_no",
                    "sorumlu_personel",
                    "kullanim_alani",
                    "bagli_makina_no",
                    "ifs_no",
                    "tarih",
                    "islem_yapan",
                ]:
                    if field in form:
                        value = form.get(field)
                        if field == "tarih":
                            value = date.fromisoformat(value) if value else None
                        setattr(item, field, value)
        else:
            item = HardwareInventory(
                no=form.get("no"),
                fabrika=form.get("fabrika"),
                blok=form.get("blok"),
                departman=form.get("departman"),
                donanim_tipi=form.get("donanim_tipi"),
                bilgisayar_adi=form.get("bilgisayar_adi"),
                marka=form.get("marka"),
                model=form.get("model"),
                seri_no=form.get("seri_no"),
                sorumlu_personel=form.get("sorumlu_personel"),
                kullanim_alani=form.get("kullanim_alani"),
                bagli_makina_no=form.get("bagli_makina_no"),
                ifs_no=form.get("ifs_no"),
                tarih=
                    date.fromisoformat(form.get("tarih"))
                    if form.get("tarih")
                    else None,
                islem_yapan=form.get("islem_yapan"),
            )
            db.add(item)
        db.commit()
    finally:
        db.close()
    return RedirectResponse("/inventory", status_code=303)


@router.post("/inventory/upload")
async def inventory_upload(excel_file: UploadFile = File(...)):
    """Accept a hardware inventory Excel upload (currently discarded)."""

    await excel_file.read()
    return RedirectResponse("/inventory", status_code=303)


@router.get("/license", response_class=HTMLResponse)
def license_page(request: Request) -> HTMLResponse:
    """Render the license inventory page."""

    context = {
        "request": request,
        "licenses": [],
        "columns": [],
        "column_widths": {},
        "lookups": {},
        "offset": 0,
        "page": 1,
        "total_pages": 1,
        "q": "",
        "per_page": 25,
        "table_name": "license",
        "filters": [],
        "count": 0,
    }
    return templates.TemplateResponse("lisans.html", context)


@router.post("/license/add")
async def license_add(request: Request):
    """Create or update a software license record."""

    form = await request.form()
    db = SessionLocal()
    try:
        license_id = form.get("license_id")
        if license_id:
            item = db.query(LicenseInventory).get(int(license_id))
            if item:
                for field in [
                    "departman",
                    "kullanici",
                    "yazilim_adi",
                    "lisans_anahtari",
                    "mail_adresi",
                    "envanter_no",
                    "ifs_no",
                    "tarih",
                    "islem_yapan",
                    "notlar",
                ]:
                    if field in form:
                        value = form.get(field)
                        if field == "tarih":
                            value = date.fromisoformat(value) if value else None
                        setattr(item, field, value)
        else:
            item = LicenseInventory(
                departman=form.get("departman"),
                kullanici=form.get("kullanici"),
                yazilim_adi=form.get("yazilim_adi"),
                lisans_anahtari=form.get("lisans_anahtari"),
                mail_adresi=form.get("mail_adresi"),
                envanter_no=form.get("envanter_no"),
                ifs_no=form.get("ifs_no"),
                tarih=
                    date.fromisoformat(form.get("tarih"))
                    if form.get("tarih")
                    else None,
                islem_yapan=form.get("islem_yapan"),
                notlar=form.get("notlar"),
            )
            db.add(item)
        db.commit()
    finally:
        db.close()
    return RedirectResponse("/license", status_code=303)


@router.post("/license/upload")
async def license_upload(excel_file: UploadFile = File(...)):
    """Accept a license inventory Excel upload (currently discarded)."""

    await excel_file.read()
    return RedirectResponse("/license", status_code=303)


@router.get("/accessories", response_class=HTMLResponse)
def accessories_page(request: Request) -> HTMLResponse:
    """Render the accessories tracking page."""

    return templates.TemplateResponse(
        "aksesuar.html", {"request": request, "items": []}
    )


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
    context = {
        "request": request,
        "groups": {},
        "lookups": lookups,
        "today": date.today().isoformat(),
    }
    return templates.TemplateResponse("talep.html", context)


@router.post("/requests/add")
async def requests_add(request: Request):
    """Add a request record."""

    form = await request.form()
    db = SessionLocal()
    try:
        item = RequestItem(
            kategori=form.get("kategori"),
            donanim_tipi=form.get("donanim_tipi"),
            marka=form.get("marka"),
            model=form.get("model"),
            yazilim_adi=form.get("yazilim_adi"),
            urun_adi=form.get("urun_adi") or form.get("model") or "",
            adet=int(form.get("adet") or 0),
            tarih=
                date.fromisoformat(form.get("tarih"))
                if form.get("tarih")
                else None,
            ifs_no=form.get("ifs_no"),
            aciklama=form.get("aciklama"),
            talep_acan=request.session.get("user", ""),
        )
        db.add(item)
        db.commit()
    finally:
        db.close()
    return RedirectResponse("/requests", status_code=303)


@router.get("/profile", response_class=HTMLResponse)
def profile_page(request: Request) -> HTMLResponse:
    """Render a simple profile page."""

    user = {"first_name": "", "last_name": "", "email": ""}
    return templates.TemplateResponse("profile.html", {"request": request, "user": user})


@router.get("/change-password", response_class=HTMLResponse)
def change_password_page(request: Request) -> HTMLResponse:
    """Render change password page."""

    return templates.TemplateResponse("change_password.html", {"request": request})


@router.get("/lists", response_class=HTMLResponse)
def lists_page(request: Request) -> HTMLResponse:
    """Render the lists management page."""

    context = {
        "request": request,
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
    return templates.TemplateResponse("listeler.html", context)


@router.post("/lists/add")
async def lists_add(item_type: str = Form(...), name: str = Form(...)):
    """Add a lookup list item."""

    db = SessionLocal()
    try:
        db.add(LookupItem(type=item_type, name=name))
        db.commit()
    finally:
        db.close()
    return RedirectResponse("/lists", status_code=303)


@router.get("/ping")
def ping() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/table-columns")
def table_columns(table_name: str) -> dict[str, list[str]]:
    """Return available columns for the requested table."""
    model = MODEL_MAP.get(table_name)
    if not model:
        return {"columns": []}
    cols = get_table_columns(model.__tablename__)
    return {"columns": cols}


@router.get("/column-settings")
def column_settings(table_name: str) -> dict:
    """Fetch stored column settings for a table."""
    settings = load_settings()
    return settings.get(table_name, {})


@router.post("/column-settings")
def save_column_settings(table_name: str, data: dict) -> dict[str, str]:
    """Persist column settings for a table."""
    settings = load_settings()
    settings[table_name] = data
    save_settings(settings)
    return {"status": "ok"}


@router.get("/column-values")
def column_values(table_name: str, column: str | None = None) -> dict[str, list]:
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
