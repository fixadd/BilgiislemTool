import os
import json
from datetime import date, timedelta
from pathlib import Path
from typing import List

from fastapi.templating import Jinja2Templates
from sqlalchemy import inspect
from sqlalchemy.orm import Session

from models import (
    engine,
    ActivityLog,
    DeletedHardwareInventory,
    DeletedPrinterInventory,
    DeletedLicenseInventory,
    DeletedStockItem,
)

TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates"
# Reusable Jinja2 template loader using an absolute path
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

# Settings file path used by load_settings/save_settings
SETTINGS_FILE = os.path.join(
    os.path.dirname(__file__), "..", "data", "column_settings.json"
)

# File storing selected stock items for dashboard display
HOME_STOCK_FILE = os.path.join(
    os.path.dirname(__file__), "..", "data", "home_stock.json"
)


def load_settings() -> dict:
    """Load column settings from disk if available."""
    if os.path.exists(SETTINGS_FILE):
        with open(SETTINGS_FILE, "r") as fh:
            return json.load(fh)
    return {}


def save_settings(data: dict) -> None:
    """Persist column settings to disk."""
    os.makedirs(os.path.dirname(SETTINGS_FILE), exist_ok=True)
    with open(SETTINGS_FILE, "w") as fh:
        json.dump(data, fh)


def load_home_stock() -> List[str]:
    """Load list of stock item names to display on the dashboard."""
    if os.path.exists(HOME_STOCK_FILE):
        with open(HOME_STOCK_FILE, "r") as fh:
            return json.load(fh)
    return []


def save_home_stock(items: List[str]) -> None:
    """Persist stock item names to display on the dashboard."""
    os.makedirs(os.path.dirname(HOME_STOCK_FILE), exist_ok=True)
    with open(HOME_STOCK_FILE, "w") as fh:
        json.dump(items, fh)


def get_table_columns(table_name: str) -> List[str]:
    """Return a list of column names for the given table."""
    columns = [col["name"] for col in inspect(engine).get_columns(table_name)]
    # Skip primary key identifiers which are not meant for display/editing
    cols = [c for c in columns if c != "id"]
    # Ensure inventory number appears first if present
    if "envanter_no" in cols:
        cols.remove("envanter_no")
        cols.insert(0, "envanter_no")
    # Ensure date and operator fields appear at the end consistently
    for field in ["tarih", "islem_yapan"]:
        if field in cols:
            cols.remove(field)
            cols.append(field)
    return cols


def cleanup_deleted(db: Session) -> None:
    """Remove soft-deleted items older than 15 days."""
    cutoff = date.today() - timedelta(days=15)
    db.query(DeletedHardwareInventory).filter(
        DeletedHardwareInventory.deleted_at < cutoff
    ).delete()
    db.query(DeletedPrinterInventory).filter(
        DeletedPrinterInventory.deleted_at < cutoff
    ).delete()
    db.query(DeletedLicenseInventory).filter(
        DeletedLicenseInventory.deleted_at < cutoff
    ).delete()
    db.query(DeletedStockItem).filter(
        DeletedStockItem.deleted_at < cutoff
    ).delete()
    db.commit()


def log_action(db: Session, username: str, action: str) -> None:
    """Record a user action in the activity log."""
    db.add(ActivityLog(username=username, action=action))
    db.commit()
