"""Stock tracking routes."""

from datetime import date

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from urllib.parse import urlencode
import os
from fastapi_csrf_protect import CsrfProtect
from pydantic_settings import BaseSettings
from sqlalchemy.orm import Session

from utils.auth import require_login
from utils import log_action
import utils
from logs import InventoryLogCreate
from services.log_service import add_inventory_log

os.environ.setdefault("FASTAPI_CSRF_SECRET", "dev-secret")


class CsrfSettings(BaseSettings):
    secret_key: str = os.environ.get("FASTAPI_CSRF_SECRET", "dev-secret")


@CsrfProtect.load_config
def load_csrf_config() -> CsrfSettings:  # pragma: no cover - simple config
    return CsrfSettings()
from models import (
    StockItem,
    HardwareInventory,
    PrinterInventory,
    LicenseInventory,
    AccessoryInventory,
    User,
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
def list_stock(
    request: Request,
    db: Session = Depends(get_db),
    kategori: str | None = None,
) -> HTMLResponse:
    """Render stock list using the common helper with optional category filter."""
    utils.engine = db.get_bind()
    params = list(request.query_params.multi_items())

    existing_kategori_filter = any(
        f == "filter_field" and v == "kategori" for f, v in params
    )

    if kategori == "license":
        return RedirectResponse("/license")

    if kategori is None and not existing_kategori_filter:
        kategori = "inventory"

    if kategori:
        params.append(("filter_field", "kategori"))
        params.append(("filter_value", kategori))
    scope = dict(request.scope)
    scope["query_string"] = urlencode(params, doseq=True).encode()
    new_request = Request(scope, request.receive)
    response = list_items(
        new_request,
        db,
        StockItem,
        table_name="stock",
        filter_fields=StockItem.__table__.columns.keys(),
        template_name="stok.html",
        items_key="stocks",
    )
    response.context["active_tab"] = kategori
    return response


@router.post("/add")
async def add_stock(request: Request, db: Session = Depends(get_db)):
    """Add a stock item."""
    form = await request.form()
    kategori = form.get("kategori")
    if not kategori:
        return JSONResponse({"detail": "kategori gerekli"}, status_code=400)
    item = StockItem(
            urun_adi=form.get("urun_adi"),
            adet=int(form.get("adet") or 0),
            kategori=kategori,
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
    db.refresh(item)

    add_inventory_log(
        InventoryLogCreate(
            inventory_type="stock",
            inventory_id=item.id,
            action="assign",
            changed_by=request.session.get("user_id", 0),
            new_location=form.get("departman"),
        )
    )
    log_action(
        db,
        request.session.get("username", ""),
        f"Added stock item {item.id}",
    )
    return RedirectResponse(f"/stock?kategori={kategori}", status_code=303)


@router.post("/assign")
async def assign_stock(request: Request, db: Session = Depends(get_db)):
    """Assign stock items to a user and move them into another inventory."""
    try:
        data = await request.json()
    except Exception:
        form = await request.form()
        data = dict(form)

    stock_id = int(data.get("stock_id") or 0)
    user_id = int(data.get("user_id") or 0)
    target = (data.get("inventory_type") or data.get("target") or "").lower()
    qty = int(data.get("quantity") or data.get("adet") or 0)

    model = INVENTORY_MODEL_MAP.get(target)
    user = db.get(User, user_id) if user_id else None
    if not model or not stock_id or qty <= 0 or not user:
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
    user_name = (f"{user.first_name or ''} {user.last_name or ''}".strip() or user.username)
    if "kullanici" in columns:
        item_data["kullanici"] = user_name
    if "sorumlu_personel" in columns:
        item_data["sorumlu_personel"] = user_name
    if "adet" in columns:
        item_data["adet"] = int(item_data.get("adet") or 1)

    for _ in range(qty):
        db.add(model(**item_data))

    stock.adet = (stock.adet or 0) - qty
    db.commit()

    add_inventory_log(
        InventoryLogCreate(
            inventory_type="stock",
            inventory_id=stock.id,
            action="assign",
            changed_by=request.session.get("user_id", 0),
            old_location=stock.departman,
            note=f"Assigned {qty} to {target} for user {user.username}",
        )
    )

    log_action(
        db,
        request.session.get("username", ""),
        f"Assigned {qty} of stock item {stock.id} to {target} for user {user.username}",
    )
    return JSONResponse({"status": "ok"})


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
    db.refresh(stock)

    add_inventory_log(
        InventoryLogCreate(
            inventory_type="stock",
            inventory_id=stock.id,
            action="move",
            changed_by=request.session.get("user_id", 0),
            old_location=stock.departman,
            note=f"Transferred {qty} to {target}",
        )
    )

    log_action(
        db,
        request.session.get("username", ""),
        f"Transferred {qty} of stock item {stock.id} to {target}",
    )
    return JSONResponse({"status": "ok", "remaining": stock.adet})
