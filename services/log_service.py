import sqlite3
from typing import List, Optional, Dict, Any

from logs import InventoryLogCreate

DB_PATH = "data/envanter.db"


def _row_to_dict(cursor, row):
    return {desc[0]: row[idx] for idx, desc in enumerate(cursor.description)}


def add_inventory_log(payload: InventoryLogCreate) -> int:
    q = """
    INSERT INTO inventory_logs
    (inventory_type, inventory_id, old_user_id, new_user_id, old_location, new_location, action, note, changed_by)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """
    with sqlite3.connect(DB_PATH) as con:
        cur = con.cursor()
        cur.execute(
            q,
            (
                payload.inventory_type,
                payload.inventory_id,
                payload.old_user_id,
                payload.new_user_id,
                payload.old_location,
                payload.new_location,
                payload.action,
                payload.note,
                payload.changed_by,
            ),
        )
        con.commit()
        return cur.lastrowid


def get_inventory_logs(
    inventory_type: Optional[str] = None,
    inventory_id: Optional[int] = None,
    limit: int = 200,
    offset: int = 0,
) -> List[Dict[str, Any]]:
    base = "SELECT * FROM inventory_logs"
    conds: List[str] = []
    params: List[Any] = []
    if inventory_type:
        conds.append("inventory_type = ?")
        params.append(inventory_type)
    if inventory_id is not None:
        conds.append("inventory_id = ?")
        params.append(inventory_id)
    if conds:
        base += " WHERE " + " AND ".join(conds)
    base += " ORDER BY change_date DESC, id DESC LIMIT ? OFFSET ?"
    params.extend([limit, offset])

    with sqlite3.connect(DB_PATH) as con:
        con.row_factory = _row_to_dict
        cur = con.cursor()
        cur.execute(base, params)
        return cur.fetchall()
