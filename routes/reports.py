from fastapi import APIRouter
import sqlite3

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
