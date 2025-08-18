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
import routes.inventory_logs as inventory_logs_module
from routes.inventory_logs import router as logs_router
from utils.auth import require_admin
import services.log_service as log_service


def create_app():
    app = FastAPI()
    app.add_middleware(SessionMiddleware, secret_key="test")
    app.include_router(logs_router)
    app.dependency_overrides[require_admin] = lambda: None
    return app


def setup_in_memory_db():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    models.engine = engine
    models.SessionLocal = TestingSessionLocal
    inventory_logs_module.SessionLocal = TestingSessionLocal
    models.Base.metadata.create_all(bind=engine)


def setup_log_db(tmp_path):
    log_db = tmp_path / "logs.db"
    with sqlite3.connect(log_db) as con:
        with open("db/migrations/001_inventory_logs.sql") as f:
            con.executescript(f.read())
        # minimal tables required for joins in get_inventory_logs
        con.execute(
            "CREATE TABLE users (id INTEGER PRIMARY KEY, username TEXT, first_name TEXT, last_name TEXT)"
        )
        con.execute("CREATE TABLE lookup_items (id INTEGER PRIMARY KEY, name TEXT)")
    log_service.DB_PATH = str(log_db)


def test_logs_page_allows_blank_user_id(tmp_path):
    setup_in_memory_db()
    setup_log_db(tmp_path)
    app = create_app()
    with TestClient(app) as client:
        resp = client.get("/logs/records?log_type=inventory&user_id=")
        assert resp.status_code == 200


def test_inventory_logs_show_user_location_changes(tmp_path):
    setup_in_memory_db()
    setup_log_db(tmp_path)
    log_db = tmp_path / "logs.db"
    with sqlite3.connect(log_db) as con:
        con.execute(
            "INSERT INTO users (id, username, first_name, last_name) VALUES (1, 'user1', 'User', 'One')"
        )
        con.execute(
            "INSERT INTO users (id, username, first_name, last_name) VALUES (2, 'user2', 'User', 'Two')"
        )
        con.execute("INSERT INTO lookup_items (id, name) VALUES (1, 'Depo1'), (2, 'Depo2')")
        con.execute(
            "CREATE TABLE hardware_inventory (id INTEGER PRIMARY KEY, bilgisayar_adi TEXT, no TEXT)"
        )
        con.execute(
            "INSERT INTO hardware_inventory (id, bilgisayar_adi, no) VALUES (10, 'PC', 'INV123')"
        )
        con.execute(
            "INSERT INTO inventory_logs (inventory_type, inventory_id, old_user_id, new_user_id, old_location, new_location, action, changed_by) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            ("pc", 10, 1, 2, "1", "2", "move", 1),
        )
        con.commit()
    app = create_app()
    with TestClient(app) as client:
        resp = client.get("/logs/records?log_type=inventory&inventory_no=INV123")
        assert resp.status_code == 200
        assert "User One &rarr; User Two" in resp.text
        assert "Depo1 &rarr; Depo2" in resp.text
