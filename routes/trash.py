from datetime import date
from typing import Dict, Tuple

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from models import (
    DeletedHardwareInventory,
    DeletedLicenseInventory,
    DeletedPrinterInventory,
    DeletedStockItem,
    HardwareInventory,
    LicenseInventory,
    PrinterInventory,
    StockItem,
    get_db,
)
from utils import log_action, templates
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
def trash_page(request: Request, db: Session = Depends(get_db)) -> HTMLResponse:
    """Render a page listing soft-deleted records."""
    hardware = db.query(DeletedHardwareInventory).all()
    licenses = db.query(DeletedLicenseInventory).all()
    printers = db.query(DeletedPrinterInventory).all()
    stocks = db.query(DeletedStockItem).all()

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
async def trash_delete(request: Request, db: Session = Depends(get_db)):
    """Permanently delete selected items from the trash."""
    form = await request.form()
    item_type = form.get("item_type")
    ids = [int(i) for i in form.getlist("ids")]
    model = DELETED_MODELS.get(item_type)
    if model and ids:
        db.query(model).filter(model.id.in_(ids)).delete(synchronize_session=False)
        log_action(
            db,
            request.session.get("username", ""),
            f"Permanently deleted {item_type} items {ids}",
        )
    return RedirectResponse("/trash", status_code=303)


def _restore_item(item_id: int, models_pair: Tuple[object, object], db: Session) -> None:
    deleted_model, active_model = models_pair
    item = db.get(deleted_model, item_id)
    if item:
        data = {
            col.name: getattr(item, col.name, None)
            for col in active_model.__table__.columns
            if col.name != "id"
        }
        restored = active_model(**data)
        db.add(restored)
        db.delete(item)


@router.post("/{item_type}/restore/{item_id}")
def restore_item(
    request: Request, item_type: str, item_id: int, db: Session = Depends(get_db)
):
    """Restore a soft-deleted item back to its active table."""
    deleted_model = DELETED_MODELS.get(item_type)
    active_model = ACTIVE_MODELS.get(item_type)
    if not deleted_model or not active_model:
        raise HTTPException(status_code=404, detail="Invalid item type")

    _restore_item(item_id, (deleted_model, active_model), db)
    log_action(
        db,
        request.session.get("username", ""),
        f"Restored {item_type} item {item_id}",
    )
    return RedirectResponse("/trash", status_code=303)
