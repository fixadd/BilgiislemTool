import sqlite3
from fastapi import FastAPI
from fastapi.testclient import TestClient
from routes import reports as reports_module


def setup_db(db_path: str):
    con = sqlite3.connect(db_path)
    with open("db/migrations/001_inventory_logs.sql") as f:
        con.executescript(f.read())
    with open("db/migrations/002_inventory_latest_view.sql") as f:
        con.executescript(f.read())
    return con


def test_current_assignments_returns_latest(tmp_path):
    db_file = tmp_path / "envanter.db"
    con = setup_db(db_file)
    cur = con.cursor()
    cur.execute(
        "INSERT INTO inventory_logs (inventory_type, inventory_id, new_user_id, new_location, action, changed_by, change_date) VALUES (?, ?, ?, ?, ?, ?, ?)",
        ("pc", 1, 10, "A", "assign", 1, "2024-01-01 10:00:00"),
    )
    cur.execute(
        "INSERT INTO inventory_logs (inventory_type, inventory_id, new_user_id, new_location, action, changed_by, change_date) VALUES (?, ?, ?, ?, ?, ?, ?)",
        ("pc", 1, 20, "B", "assign", 2, "2024-01-02 10:00:00"),
    )
    cur.execute(
        "INSERT INTO inventory_logs (inventory_type, inventory_id, new_user_id, new_location, action, changed_by, change_date) VALUES (?, ?, ?, ?, ?, ?, ?)",
        ("pc", 2, 30, "C", "assign", 3, "2024-01-03 10:00:00"),
    )
    con.commit()
    con.close()

    reports_module.DB_PATH = str(db_file)
    app = FastAPI()
    app.include_router(reports_module.router)
    with TestClient(app) as client:
        resp = client.get("/reports/current-assignments?inv_type=pc")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 2
        item1 = [d for d in data if d["inventory_id"] == 1][0]
        assert item1["user_id"] == 20
