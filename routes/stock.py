"""Stock tracking routes."""

from datetime import date

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from sqlalchemy.orm import Session

from utils.auth import require_login
from utils import log_action
from models import (
    StockItem,
    HardwareInventory,
    PrinterInventory,
    LicenseInventory,
    AccessoryInventory,
    get_db,
)
from routes.common_list import list_items

router = APIRouter(dependencies=[Depends(require_login)])

# Map supported inventory type identifiers to their respective models
INVENTORY_MODEL_MAP = {
    "inventory": HardwareInventory,
    "hardware": HardwareInventory,
    "donanim": HardwareInventory,
    "printer": PrinterInventory,
    "license": LicenseInventory,
    "lisans": LicenseInventory,
    "accessory": AccessoryInventory,
    "aksesuar": AccessoryInventory,
}


@router.get("", response_class=HTMLResponse)
def list_stock(request: Request, db: Session = Depends(get_db)) -> HTMLResponse:
    """Render stock list using the common helper."""
    return list_items(
        request,
        db,
        StockItem,
        table_name="stock",
        filter_fields=StockItem.__table__.columns.keys(),
        template_name="stok.html",
        items_key="stocks",
    )


@router.post("/add")
async def add_stock(request: Request, db: Session = Depends(get_db)):
    """Add a stock item."""
    form = await request.form()
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
    log_action(
        db,
        request.session.get("username", ""),
        f"Added stock item {item.id}",
    )
    return RedirectResponse("/stock", status_code=303)


@router.post("/transfer")
async def transfer_stock(request: Request, db: Session = Depends(get_db)):
    """Transfer stock items into another inventory type."""
    try:
        data = await request.json()
    except Exception:
        form = await request.form()
        data = dict(form)

    stock_id = int(data.get("stock_id") or data.get("id") or 0)
    target = (data.get("inventory_type") or data.get("target") or "").lower()
    qty = int(data.get("quantity") or data.get("adet") or 0)

    model = INVENTORY_MODEL_MAP.get(target)
    if not model or not stock_id or qty <= 0:
        return JSONResponse({"status": "error"}, status_code=400)

    stock = db.get(StockItem, stock_id)
    if not stock or (stock.adet or 0) < qty:
        return JSONResponse({"status": "error"}, status_code=400)

    columns = set(model.__table__.columns.keys()) - {"id"}
    item_data = {k: v for k, v in data.items() if k in columns}
    if "tarih" in columns and "tarih" not in item_data:
        item_data["tarih"] = date.today()
    if "ifs_no" in columns and "ifs_no" not in item_data:
        item_data["ifs_no"] = stock.ifs_no
    if "aciklama" in columns and "aciklama" not in item_data:
        item_data["aciklama"] = stock.aciklama
    if "urun_adi" in columns and "urun_adi" not in item_data:
        item_data["urun_adi"] = stock.urun_adi
    if "islem_yapan" in columns:
        item_data["islem_yapan"] = request.session.get("full_name", "")
    if "adet" in columns:
        item_data["adet"] = int(item_data.get("adet") or 1)

    for _ in range(qty):
        db.add(model(**item_data))

    stock.adet = (stock.adet or 0) - qty
    db.commit()

    log_action(
        db,
        request.session.get("username", ""),
        f"Transferred {qty} of stock item {stock.id} to {target}",
    )
    return JSONResponse({"status": "ok"})
