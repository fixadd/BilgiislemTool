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
    # Base queries: one using inventory number columns (for newer schemas)
    # and a fallback without them for backwards compatibility.
    base_with_inv = (
        "SELECT il.*, "
        "COALESCE(il.new_inventory_no, il.old_inventory_no) AS inventory_no, "
        "COALESCE(TRIM(uo.first_name || ' ' || uo.last_name), uo.username) AS old_user_name, "
        "COALESCE(TRIM(un.first_name || ' ' || un.last_name), un.username) AS new_user_name, "
        "COALESCE(TRIM(uc.first_name || ' ' || uc.last_name), uc.username) AS changed_by_name, "
        "COALESCE(olo.name, il.old_location) AS old_location, "
        "COALESCE(nlo.name, il.new_location) AS new_location "
        "FROM inventory_logs il "
        "LEFT JOIN users uo ON il.old_user_id = uo.id "
        "LEFT JOIN users un ON il.new_user_id = un.id "
        "LEFT JOIN users uc ON il.changed_by = uc.id "
        "LEFT JOIN lookup_items olo ON CAST(il.old_location AS INTEGER) = olo.id "
        "LEFT JOIN lookup_items nlo ON CAST(il.new_location AS INTEGER) = nlo.id"
    )
    base_legacy = (
        "SELECT il.*, "
        "COALESCE(TRIM(uo.first_name || ' ' || uo.last_name), uo.username) AS old_user_name, "
        "COALESCE(TRIM(un.first_name || ' ' || un.last_name), un.username) AS new_user_name, "
        "COALESCE(TRIM(uc.first_name || ' ' || uc.last_name), uc.username) AS changed_by_name, "
        "COALESCE(olo.name, il.old_location) AS old_location, "
        "COALESCE(nlo.name, il.new_location) AS new_location "
        "FROM inventory_logs il "
        "LEFT JOIN users uo ON il.old_user_id = uo.id "
        "LEFT JOIN users un ON il.new_user_id = un.id "
        "LEFT JOIN users uc ON il.changed_by = uc.id "
        "LEFT JOIN lookup_items olo ON CAST(il.old_location AS INTEGER) = olo.id "
        "LEFT JOIN lookup_items nlo ON CAST(il.new_location AS INTEGER) = nlo.id"
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
    def build_query(base: str) -> str:
        q = base
        if conds:
            q += " WHERE " + " AND ".join(conds)
        q += " ORDER BY il.change_date DESC, il.id DESC LIMIT ? OFFSET ?"
        return q

    params.extend([limit, offset])

    with sqlite3.connect(DB_PATH) as con:
        con.row_factory = _row_to_dict
        cur = con.cursor()
        try:
            cur.execute(build_query(base_with_inv), params)
        except sqlite3.OperationalError:
            cur.execute(build_query(base_legacy), params)
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
        ("accessory", "accessory_inventory", "urun_adi", "ifs_no"),
        ("stock", "stock_tracking", "urun_adi", "id"),
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
    # Ensure the inventory number is treated as a string when sorting so that
    # numeric IDs (e.g., from stock items) don't cause comparisons between
    # ``int`` and ``str`` types.
    rows.sort(key=lambda r: str(r[3]) if r[3] is not None else "")
    return [
        {
            "type": r[0],
            "id": r[1],
            "name": r[2],
            "inv_no": str(r[3]) if r[3] is not None else None,
        }
        for r in rows
    ]


def get_inventory_no(inventory_type: str, inventory_id: int) -> Optional[str]:
    """Return the inventory number for the given item, if available."""
    mapping = {
        "pc": ("hardware_inventory", "no"),
        "license": ("license_inventory", "envanter_no"),
    }
    table_col = mapping.get(inventory_type)
    if not table_col:
        return None
    table, col = table_col
    with sqlite3.connect(DB_PATH) as con:
        cur = con.cursor()
        try:
            cur.execute(f"SELECT {col} FROM {table} WHERE id = ?", (inventory_id,))
            row = cur.fetchone()
            return row[0] if row else None
        except sqlite3.OperationalError:
            return None


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
