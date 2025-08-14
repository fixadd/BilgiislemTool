from datetime import date
from typing import Dict, Tuple

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from models import (
    SessionLocal,
    DeletedHardwareInventory,
    DeletedLicenseInventory,
    DeletedPrinterInventory,
    DeletedStockItem,
    HardwareInventory,
    LicenseInventory,
    PrinterInventory,
    StockItem,
)
from utils import templates
from utils.auth import require_login

router = APIRouter(dependencies=[Depends(require_login)])

# Mapping for easier model lookup
DELETED_MODELS: Dict[str, object] = {
    "hardware": DeletedHardwareInventory,
    "license": DeletedLicenseInventory,
    "printer": DeletedPrinterInventory,
    "stock": DeletedStockItem,
}

ACTIVE_MODELS: Dict[str, object] = {
    "hardware": HardwareInventory,
    "license": LicenseInventory,
    "printer": PrinterInventory,
    "stock": StockItem,
}


@router.get("/trash", response_class=HTMLResponse)
def trash_page(request: Request) -> HTMLResponse:
    """Render a page listing soft-deleted records."""
    db = SessionLocal()
    try:
        hardware = db.query(DeletedHardwareInventory).all()
        licenses = db.query(DeletedLicenseInventory).all()
        printers = db.query(DeletedPrinterInventory).all()
        stocks = db.query(DeletedStockItem).all()
    finally:
        db.close()

    context = {
        "request": request,
        "hardware": hardware,
        "licenses": licenses,
        "printers": printers,
        "stocks": stocks,
        "today": date.today(),
    }
    return templates.TemplateResponse("trash.html", context)


@router.post("/trash/delete")
async def trash_delete(request: Request):
    """Permanently delete selected items from the trash."""
    form = await request.form()
    item_type = form.get("item_type")
    ids = [int(i) for i in form.getlist("ids")]
    model = DELETED_MODELS.get(item_type)
    db = SessionLocal()
    try:
        if model and ids:
            db.query(model).filter(model.id.in_(ids)).delete(synchronize_session=False)
            db.commit()
    finally:
        db.close()
    return RedirectResponse("/trash", status_code=303)


def _restore_item(item_id: int, models_pair: Tuple[object, object]) -> None:
    deleted_model, active_model = models_pair
    db = SessionLocal()
    try:
        item = db.query(deleted_model).get(item_id)
        if item:
            data = {
                col.name: getattr(item, col.name, None)
                for col in active_model.__table__.columns
                if col.name != "id"
            }
            restored = active_model(**data)
            db.add(restored)
            db.delete(item)
            db.commit()
    finally:
        db.close()


@router.post("/inventory/restore/{item_id}")
def restore_hardware(item_id: int):
    _restore_item(item_id, (DeletedHardwareInventory, HardwareInventory))
    return RedirectResponse("/trash", status_code=303)


@router.post("/license/restore/{item_id}")
def restore_license(item_id: int):
    _restore_item(item_id, (DeletedLicenseInventory, LicenseInventory))
    return RedirectResponse("/trash", status_code=303)


@router.post("/printer/restore/{item_id}")
def restore_printer(item_id: int):
    _restore_item(item_id, (DeletedPrinterInventory, PrinterInventory))
    return RedirectResponse("/trash", status_code=303)


@router.post("/stock/restore/{item_id}")
def restore_stock(item_id: int):
    _restore_item(item_id, (DeletedStockItem, StockItem))
    return RedirectResponse("/trash", status_code=303)
