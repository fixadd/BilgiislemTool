"""Inventory management related endpoints."""

from datetime import date, datetime

import csv
from io import StringIO

from fastapi import APIRouter, Body, Depends, File, Request, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, StreamingResponse
from sqlalchemy.orm import Session

from utils.auth import require_login
from models import (
    AccessoryInventory,
    HardwareInventory,
    LicenseInventory,
    PrinterInventory,
    StockItem,
    DeletedHardwareInventory,
    DeletedLicenseInventory,
    DeletedPrinterInventory,
    DeletedAccessoryInventory,
    DeletedStockItem,
    get_db,
    SessionLocal,
)
from utils import get_table_columns, load_settings, save_settings, log_action
from logs import InventoryLogCreate
from services.log_service import add_inventory_log
from .stock import list_stock as stock_list


router = APIRouter(dependencies=[Depends(require_login)])


# Mapping from short table identifiers used in the UI to the actual
# SQLAlchemy model classes. This allows API endpoints to operate on
# different tables in a generic manner.
MODEL_MAP = {
    "stock": StockItem,
    "printer": PrinterInventory,
    "license": LicenseInventory,
    "inventory": HardwareInventory,
    "accessory": AccessoryInventory,
}


@router.get("/inventory/fetch/{no}")
def inventory_fetch(no: str, db: Session = Depends(get_db)):
    """Fetch hardware inventory details by inventory number."""
    item = db.query(HardwareInventory).filter(HardwareInventory.no == no).first()
    if not item:
        return JSONResponse({"status": "not_found"}, status_code=404)
    return {
        "departman": item.departman,
        "sorumlu_personel": item.sorumlu_personel,
        "kullanim_alani": item.kullanim_alani,
        "bilgisayar_adi": item.bilgisayar_adi,
        "marka": item.marka,
        "model": item.model,
        # Provide a generic product name for accessory lookups
        "urun_adi": item.bilgisayar_adi,
    }


def _export_model(model, filename: str, db: Session) -> StreamingResponse:
    """Export all records of a model as CSV."""
    items = db.query(model).all()
    output = StringIO()
    writer = csv.writer(output)
    columns = [col.name for col in model.__table__.columns]
    writer.writerow(columns)
    for item in items:
        row = []
        for col in columns:
            value = getattr(item, col)
            if isinstance(value, (date, datetime)):
                value = value.isoformat()
            row.append(value)
        writer.writerow(row)
    output.seek(0)
    return StreamingResponse(
        output,
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


def _soft_delete(ids: list[int], model, deleted_model, db: Session) -> None:
    """Move selected records to their deleted counterparts."""
    if not ids:
        return
    records = db.query(model).filter(model.id.in_(ids)).all()
    for record in records:
        data = {
            col.name: getattr(record, col.name)
            for col in model.__table__.columns
            if col.name != "id"
        }
        deleted = deleted_model(**data, deleted_at=date.today())
        db.add(deleted)
        db.delete(record)
    db.commit()


@router.post("/stock/add")
async def stock_add(request: Request, db: Session = Depends(get_db)):
    """Create or update a stock item from form data."""
    form = await request.form()
    stock_id = form.get("stock_id")
    if stock_id:
        item = db.get(StockItem, int(stock_id))
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
            ]:
                if field in form:
                    value = form.get(field)
                    if field in {"adet"}:
                        value = int(value) if value else None
                    elif field in {"guncelleme_tarihi", "tarih"}:
                        value = date.fromisoformat(value) if value else None
                    setattr(item, field, value)
            item.islem_yapan = request.session.get("full_name", "")
        action = f"Updated stock item {stock_id}"
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
            islem_yapan=request.session.get("full_name", ""),
        )
        db.add(item)
        action = f"Added stock item {item.id}"
    log_action(db, request.session.get("username", ""), action)
    return RedirectResponse("/stock", status_code=303)


@router.get("/stock", response_class=HTMLResponse)
def stock_list_page(request: Request, db: Session = Depends(get_db)) -> HTMLResponse:
    """Render the stock list page."""
    return stock_list(request, db)


@router.post("/printer/add")
async def printer_add(request: Request, db: Session = Depends(get_db)):
    """Create or update a printer inventory item."""
    form = await request.form()
    printer_id = form.get("printer_id")
    if printer_id:
        existing = db.get(PrinterInventory, int(printer_id))
        if existing:
            data = {
                col.name: getattr(existing, col.name)
                for col in PrinterInventory.__table__.columns
                if col.name != "id"
            }
            deleted = DeletedPrinterInventory(**data, deleted_at=date.today())
            db.add(deleted)
            for field in [
                "envanter_no",
                "yazici_markasi",
                "yazici_modeli",
                "kullanim_alani",
                "ip_adresi",
                "mac",
                "hostname",
                "notlar",
            ]:
                if field in form:
                    data[field] = form.get(field)
            data["tarih"] = date.today()
            data["islem_yapan"] = request.session.get("full_name", "")
            item = PrinterInventory(**data)
            db.add(item)
            db.delete(existing)
        action = f"Updated printer item {printer_id}"
    else:
        item = PrinterInventory(
            envanter_no=form.get("envanter_no"),
            yazici_markasi=form.get("yazici_markasi"),
            yazici_modeli=form.get("yazici_modeli"),
            kullanim_alani=form.get("kullanim_alani"),
            ip_adresi=form.get("ip_adresi"),
            mac=form.get("mac"),
            hostname=form.get("hostname"),
            tarih=date.today(),
            islem_yapan=request.session.get("full_name", ""),
            notlar=form.get("notlar"),
        )
        db.add(item)
        action = f"Added printer item {item.id}"
    log_action(db, request.session.get("username", ""), action)
    return RedirectResponse("/printer", status_code=303)


@router.post("/inventory/add")
async def inventory_add(request: Request):
    """Create or update a hardware inventory record."""
    form = await request.form()
    db = SessionLocal()
    try:
        item_id = form.get("item_id")
        relabel = False
        old_user = None
        new_user = None
        if item_id:
            existing = db.get(HardwareInventory, int(item_id))
            if existing:
                old_no = existing.no
                old_user = existing.sorumlu_personel
                data = {
                    col.name: getattr(existing, col.name)
                    for col in HardwareInventory.__table__.columns
                    if col.name != "id"
                }
                deleted = DeletedHardwareInventory(**data, deleted_at=date.today())
                db.add(deleted)
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
                ]:
                    if field in form:
                        data[field] = form.get(field)
                new_user = data.get("sorumlu_personel")
                data["tarih"] = date.today()
                data["islem_yapan"] = request.session.get("full_name", "")
                new_no = data.get("no")
                item = HardwareInventory(**data)
                db.add(item)
                db.delete(existing)
                action = f"Updated hardware item {item_id}"
                relabel = old_no != new_no
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
                    tarih=date.today(),
                    islem_yapan=request.session.get("full_name", ""),
                )
                db.add(item)
                action = f"Added hardware item {item.id}"
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
                tarih=date.today(),
                islem_yapan=request.session.get("full_name", ""),
            )
            db.add(item)
            action = f"Added hardware item {item.id}"
        db.commit()
        if item_id and old_user != new_user:
            add_inventory_log(
                InventoryLogCreate(
                    inventory_type="pc",
                    inventory_id=item.id,
                    action="assign" if new_user else "return",
                    changed_by=request.session.get("user_id", 0),
                    old_user_id=int(old_user) if old_user and str(old_user).isdigit() else None,
                    new_user_id=int(new_user) if new_user and str(new_user).isdigit() else None,
                    new_inventory_no=item.no,
                )
            )
        if item_id and relabel:
            add_inventory_log(
                InventoryLogCreate(
                    inventory_type="pc",
                    inventory_id=item.id,
                    action="relabel",
                    changed_by=request.session.get("user_id", 0),
                    old_inventory_no=old_no,
                    new_inventory_no=new_no,
                )
            )
        log_action(db, request.session.get("username", ""), action)
    finally:
        db.close()
    return RedirectResponse("/inventory", status_code=303)


@router.post("/license/add")
async def license_add(request: Request):
    """Create or update a software license record."""
    form = await request.form()
    db = SessionLocal()
    try:
        license_id = form.get("license_id")
        relabel = False
        old_user = None
        new_user = None
        if license_id:
            existing = db.get(LicenseInventory, int(license_id))
            if existing:
                old_no = existing.envanter_no
                old_user = existing.kullanici
                data = {
                    col.name: getattr(existing, col.name)
                    for col in LicenseInventory.__table__.columns
                    if col.name != "id"
                }
                deleted = DeletedLicenseInventory(**data, deleted_at=date.today())
                db.add(deleted)
                for field in [
                    "departman",
                    "kullanici",
                    "yazilim_adi",
                    "lisans_anahtari",
                    "mail_adresi",
                    "envanter_no",
                    "notlar",
                ]:
                    if field in form:
                        data[field] = form.get(field)
                new_user = data.get("kullanici")
                data["tarih"] = date.today()
                data["islem_yapan"] = request.session.get("full_name", "")
                new_no = data.get("envanter_no")
                item = LicenseInventory(**data)
                db.add(item)
                db.delete(existing)
                action = f"Updated license item {license_id}"
                relabel = old_no != new_no
            else:
                item = LicenseInventory(
                    departman=form.get("departman"),
                    kullanici=form.get("kullanici"),
                    yazilim_adi=form.get("yazilim_adi"),
                    lisans_anahtari=form.get("lisans_anahtari"),
                    mail_adresi=form.get("mail_adresi"),
                    envanter_no=form.get("envanter_no"),
                    tarih=date.today(),
                    islem_yapan=request.session.get("full_name", ""),
                    notlar=form.get("notlar"),
                )
                db.add(item)
                action = f"Added license item {item.id}"
        else:
            item = LicenseInventory(
                departman=form.get("departman"),
                kullanici=form.get("kullanici"),
                yazilim_adi=form.get("yazilim_adi"),
                lisans_anahtari=form.get("lisans_anahtari"),
                mail_adresi=form.get("mail_adresi"),
                envanter_no=form.get("envanter_no"),
                tarih=date.today(),
                islem_yapan=request.session.get("full_name", ""),
                notlar=form.get("notlar"),
            )
            db.add(item)
            action = f"Added license item {item.id}"
        db.commit()
        if license_id and old_user != new_user:
            add_inventory_log(
                InventoryLogCreate(
                    inventory_type="license",
                    inventory_id=item.id,
                    action="assign" if new_user else "return",
                    changed_by=request.session.get("user_id", 0),
                    old_user_id=int(old_user) if old_user and str(old_user).isdigit() else None,
                    new_user_id=int(new_user) if new_user and str(new_user).isdigit() else None,
                    new_inventory_no=item.envanter_no,
                )
            )
        if license_id and relabel:
            add_inventory_log(
                InventoryLogCreate(
                    inventory_type="license",
                    inventory_id=item.id,
                    action="relabel",
                    changed_by=request.session.get("user_id", 0),
                    old_inventory_no=old_no,
                    new_inventory_no=new_no,
                )
            )
        log_action(db, request.session.get("username", ""), action)
    finally:
        db.close()
    return RedirectResponse("/license", status_code=303)


@router.post("/license/upload")
async def license_upload(request: Request, excel_file: UploadFile = File(...)):
    """Accept a license inventory Excel upload (currently discarded)."""
    await excel_file.read()
    return RedirectResponse("/license", status_code=303)


@router.post("/accessories/add")
async def accessories_add(request: Request, db: Session = Depends(get_db)):
    """Create or update an accessory inventory item."""
    form = await request.form()
    accessory_id = form.get("accessory_id")
    old_user = None
    new_user = None
    if accessory_id:
        existing = db.get(AccessoryInventory, int(accessory_id))
        if existing:
            old_user = existing.kullanici
            data = {
                col.name: getattr(existing, col.name)
                for col in AccessoryInventory.__table__.columns
                if col.name != "id"
            }
            deleted = DeletedAccessoryInventory(**data, deleted_at=date.today())
            db.add(deleted)
            for field in [
                "urun_adi",
                "adet",
                "departman",
                "kullanici",
                "aciklama",
            ]:
                if field in form:
                    value = form.get(field)
                    if field == "adet":
                        value = int(value) if value else None
                    data[field] = value
            new_user = data.get("kullanici")
            data["tarih"] = date.today()
            data["islem_yapan"] = request.session.get("full_name", "")
            item = AccessoryInventory(**data)
            db.add(item)
            db.delete(existing)
            action = f"Updated accessory item {accessory_id}"
        else:
            item = AccessoryInventory(
                urun_adi=form.get("urun_adi"),
                adet=int(form.get("adet") or 0),
                tarih=date.today(),
                departman=form.get("departman"),
                kullanici=form.get("kullanici"),
                aciklama=form.get("aciklama"),
                islem_yapan=request.session.get("full_name", ""),
            )
        db.add(item)
        action = f"Added accessory item {item.id}"
    else:
        item = AccessoryInventory(
            urun_adi=form.get("urun_adi"),
            adet=int(form.get("adet") or 0),
            tarih=date.today(),
            departman=form.get("departman"),
            kullanici=form.get("kullanici"),
            aciklama=form.get("aciklama"),
            islem_yapan=request.session.get("full_name", ""),
        )
        db.add(item)
        action = f"Added accessory item {item.id}"
    db.commit()
    if accessory_id and old_user != new_user:
        add_inventory_log(
            InventoryLogCreate(
                inventory_type="accessory",
                inventory_id=item.id,
                action="assign" if new_user else "return",
                changed_by=request.session.get("user_id", 0),
                old_user_id=int(old_user) if old_user and str(old_user).isdigit() else None,
                new_user_id=int(new_user) if new_user and str(new_user).isdigit() else None,
            )
        )
    log_action(db, request.session.get("username", ""), action)
    return RedirectResponse("/accessories", status_code=303)


@router.post("/accessories/upload")
async def accessories_upload(request: Request, excel_file: UploadFile = File(...)):
    """Accept an accessories inventory Excel upload (currently discarded)."""
    await excel_file.read()
    return RedirectResponse("/accessories", status_code=303)


@router.get("/accessories/export")
def accessories_export(db: Session = Depends(get_db)):
    """Export accessories inventory as CSV."""
    return _export_model(AccessoryInventory, "accessories.csv", db)


@router.get("/inventory/export")
def inventory_export(db: Session = Depends(get_db)):
    """Export hardware inventory as CSV."""
    return _export_model(HardwareInventory, "inventory.csv", db)


@router.get("/stock/export")
def stock_export(db: Session = Depends(get_db)):
    """Export stock items as CSV."""
    return _export_model(StockItem, "stock.csv", db)


@router.get("/license/export")
def license_export(db: Session = Depends(get_db)):
    """Export license inventory as CSV."""
    return _export_model(LicenseInventory, "license.csv", db)


@router.get("/printer/export")
def printer_export(db: Session = Depends(get_db)):
    """Export printer inventory as CSV."""
    return _export_model(PrinterInventory, "printer.csv", db)


@router.post("/inventory/delete")
async def inventory_delete(request: Request):
    """Soft delete selected hardware inventory items."""
    body = await request.json()
    ids = [int(i) for i in body.get("ids", [])]
    _soft_delete(ids, HardwareInventory, DeletedHardwareInventory)
    db = SessionLocal()
    try:
        log_action(
            db,
            request.session.get("username", ""),
            f"Deleted hardware items {ids}",
        )
    finally:
        db.close()
    return {"status": "ok"}


@router.post("/stock/delete")
async def stock_delete(request: Request):
    """Soft delete selected stock items."""
    body = await request.json()
    ids = [int(i) for i in body.get("ids", [])]
    _soft_delete(ids, StockItem, DeletedStockItem)
    db = SessionLocal()
    try:
        log_action(
            db,
            request.session.get("username", ""),
            f"Deleted stock items {ids}",
        )
    finally:
        db.close()
    return {"status": "ok"}


@router.post("/license/delete")
async def license_delete(request: Request):
    """Soft delete selected license items."""
    body = await request.json()
    ids = [int(i) for i in body.get("ids", [])]
    _soft_delete(ids, LicenseInventory, DeletedLicenseInventory)
    db = SessionLocal()
    try:
        log_action(
            db,
            request.session.get("username", ""),
            f"Deleted license items {ids}",
        )
    finally:
        db.close()
    return {"status": "ok"}


@router.post("/printer/delete")
async def printer_delete(request: Request):
    """Soft delete selected printer inventory items."""
    body = await request.json()
    ids = [int(i) for i in body.get("ids", [])]
    _soft_delete(ids, PrinterInventory, DeletedPrinterInventory)
    db = SessionLocal()
    try:
        log_action(
            db,
            request.session.get("username", ""),
            f"Deleted printer items {ids}",
        )
    finally:
        db.close()
    return {"status": "ok"}


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
def save_column_settings(request: Request, table_name: str, data: dict = Body(...)):
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

