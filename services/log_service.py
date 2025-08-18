import sqlite3
from typing import List, Optional, Dict, Any

from logs import InventoryLogCreate

DB_PATH = "data/envanter.db"


def _row_to_dict(cursor, row):
    return {desc[0]: row[idx] for idx, desc in enumerate(cursor.description)}


def add_inventory_log(payload: InventoryLogCreate) -> int:
    q = """
    INSERT INTO inventory_logs
    (inventory_type, inventory_id, old_user_id, new_user_id, old_location, new_location, old_inventory_no, new_inventory_no, action, note, changed_by)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                payload.old_inventory_no,
                payload.new_inventory_no,
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
    user_id: Optional[int] = None,
    limit: int = 200,
    offset: int = 0,
) -> List[Dict[str, Any]]:
    base = (
        "SELECT il.*, uo.username AS old_user_name, un.username AS new_user_name "
        "FROM inventory_logs il "
        "LEFT JOIN users uo ON il.old_user_id = uo.id "
        "LEFT JOIN users un ON il.new_user_id = un.id"
    )
    conds: List[str] = []
    params: List[Any] = []
    if inventory_type:
        conds.append("il.inventory_type = ?")
        params.append(inventory_type)
    if inventory_id is not None:
        conds.append("il.inventory_id = ?")
        params.append(inventory_id)
    if user_id is not None:
        conds.append("(il.old_user_id = ? OR il.new_user_id = ?)")
        params.extend([user_id, user_id])
    if conds:
        base += " WHERE " + " AND ".join(conds)
    base += " ORDER BY il.change_date DESC, il.id DESC LIMIT ? OFFSET ?"
    params.extend([limit, offset])

    with sqlite3.connect(DB_PATH) as con:
        con.row_factory = _row_to_dict
        cur = con.cursor()
        cur.execute(base, params)
        return cur.fetchall()


def get_activity_logs(
    username: Optional[str] = None, limit: int = 200, offset: int = 0
) -> List[Dict[str, Any]]:
    q = "SELECT * FROM activity_log"
    conds: List[str] = []
    params: List[Any] = []
    if username:
        conds.append("username = ?")
        params.append(username)
    if conds:
        q += " WHERE " + " AND ".join(conds)
    q += " ORDER BY timestamp DESC, id DESC LIMIT ? OFFSET ?"
    params.extend([limit, offset])
    with sqlite3.connect(DB_PATH) as con:
        con.row_factory = _row_to_dict
        cur = con.cursor()
        cur.execute(q, params)
        return cur.fetchall()


def get_inventory_items() -> List[Dict[str, Any]]:
    """Return basic info for inventory items including their numbers."""
    rows = []
    parts = [
        ("pc", "hardware_inventory", "bilgisayar_adi", "no"),
        ("license", "license_inventory", "yazilim_adi", "envanter_no"),
    ]
    with sqlite3.connect(DB_PATH) as con:
        cur = con.cursor()
        for inv_type, table, name_col, no_col in parts:
            try:
                cur.execute(
                    f"SELECT ?, id, {name_col}, {no_col} FROM {table}",
                    (inv_type,),
                )
                rows.extend(cur.fetchall())
            except sqlite3.OperationalError:
                continue
    rows.sort(key=lambda r: (r[3] or ""))
    return [
        {"type": r[0], "id": r[1], "name": r[2], "inv_no": r[3]}
        for r in rows
    ]


def get_latest_assignments(limit: int = 200, offset: int = 0) -> List[Dict[str, Any]]:
    q = (
        "SELECT v.inventory_type, v.inventory_id, v.new_user_id, u.username AS new_user_name, "
        "v.new_location, v.action, v.change_date, v.id "
        "FROM v_inventory_latest v "
        "LEFT JOIN users u ON v.new_user_id = u.id "
        "ORDER BY v.change_date DESC, v.id DESC LIMIT ? OFFSET ?"
    )
    with sqlite3.connect(DB_PATH) as con:
        con.row_factory = _row_to_dict
        cur = con.cursor()
        cur.execute(q, (limit, offset))
        return cur.fetchall()
