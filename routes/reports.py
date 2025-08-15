from fastapi import APIRouter, Query
import sqlite3
from services.log_service import get_inventory_logs

router = APIRouter(prefix="/reports", tags=["Reports"])
DB_PATH = "data/envanter.db"


@router.get("/who-has-what")
def who_has_what():
    data = {}
    with sqlite3.connect(DB_PATH) as con:
        cur = con.cursor()
        cur.execute(
            "SELECT id, sorumlu_personel FROM hardware_inventory WHERE sorumlu_personel IS NOT NULL AND sorumlu_personel != ''"
        )
        data["pc"] = [{"pc_id": r[0], "user": r[1]} for r in cur.fetchall()]
        cur.execute(
            "SELECT id, kullanici FROM license_inventory WHERE kullanici IS NOT NULL AND kullanici != ''"
        )
        data["licenses"] = [{"license_id": r[0], "user": r[1]} for r in cur.fetchall()]
        cur.execute(
            "SELECT id, kullanici FROM accessory_inventory WHERE kullanici IS NOT NULL AND kullanici != ''"
        )
        data["accessories"] = [{"accessory_id": r[0], "user": r[1]} for r in cur.fetchall()]
    return data


@router.get("/current-assignments")
def current_assignments(
    inv_type: str | None = Query(default=None),
    user_id: int | None = Query(default=None),
    limit: int = 200,
    offset: int = 0,
):
    q = """
      SELECT inventory_type, inventory_id, new_user_id, new_location, action, change_date, id
      FROM v_inventory_latest
    """
    conds, params = [], []
    if inv_type:
        conds.append("inventory_type = ?")
        params.append(inv_type)
    if user_id is not None:
        conds.append("new_user_id = ?")
        params.append(user_id)
    if conds:
        q += " WHERE " + " AND ".join(conds)
    q += " ORDER BY change_date DESC, id DESC LIMIT ? OFFSET ?"
    params.extend([limit, offset])

    with sqlite3.connect(DB_PATH) as con:
        cur = con.cursor()
        cur.execute(q, params)
        rows = cur.fetchall()
    return [
        {
            "inventory_type": r[0],
            "inventory_id": r[1],
            "user_id": r[2],
            "location": r[3],
            "action": r[4],
            "change_date": r[5],
            "log_id": r[6],
        }
        for r in rows
    ]


@router.get("/user-history")
def user_history(user_id: int, limit: int = 200, offset: int = 0):
    return get_inventory_logs(user_id=user_id, limit=limit, offset=offset)
