import os
import sys
import sqlite3
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from starlette.middleware.sessions import SessionMiddleware

sys.path.append(os.path.dirname(os.path.dirname(__file__)))

import models
import routes.inventory as inventory_module
from routes.inventory import router as inventory_router
from utils.auth import require_login
import services.log_service as log_service


def setup_db():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    models.engine = engine
    models.SessionLocal = TestingSessionLocal
    original_inventory_session = inventory_module.SessionLocal
    inventory_module.SessionLocal = TestingSessionLocal
    models.Base.metadata.create_all(bind=engine)
    return original_inventory_session


def create_app():
    app = FastAPI()
    app.add_middleware(SessionMiddleware, secret_key="test")
    app.include_router(inventory_router)
    app.dependency_overrides[require_login] = lambda: None
    return app


def setup_log_db(path):
    con = sqlite3.connect(path)
    for mig in ["001_inventory_logs.sql", "003_add_inventory_no_columns.sql"]:
        with open(f"db/migrations/{mig}") as f:
            con.executescript(f.read())
    con.execute("CREATE TABLE users (id INTEGER PRIMARY KEY, username TEXT)")
    con.commit()
    con.close()


def test_inventory_log_contains_inventory_no(tmp_path):
    original_session = setup_db()
    log_db = tmp_path / "log.db"
    setup_log_db(log_db)
    log_service.DB_PATH = str(log_db)
    app = create_app()
    with TestClient(app) as client:
        resp = client.post(
            "/inventory/add",
            data={"no": "001", "donanim_tipi": "Laptop", "sorumlu_personel": "1"},
            follow_redirects=False,
        )
        assert resp.status_code == 303
        db = models.SessionLocal()
        item_id = db.query(models.HardwareInventory).first().id
        db.close()
        resp = client.post(
            "/inventory/add",
            data={
                "item_id": item_id,
                "no": "001",
                "donanim_tipi": "Laptop",
                "sorumlu_personel": "2",
            },
            follow_redirects=False,
        )
        assert resp.status_code == 303
    with sqlite3.connect(log_db) as con:
        row = con.execute("SELECT new_inventory_no FROM inventory_logs").fetchone()
    assert row[0] == "001"
    inventory_module.SessionLocal = original_session
