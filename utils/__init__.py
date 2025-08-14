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


def get_table_columns(table_name: str) -> List[str]:
    """Return a list of column names for the given table."""
    columns = [col["name"] for col in inspect(engine).get_columns(table_name)]
    # Skip primary key identifiers which are not meant for display/editing
    return [c for c in columns if c != "id"]


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
