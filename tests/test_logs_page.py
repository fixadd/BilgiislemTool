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
        # minimal users table required for joins in get_inventory_logs
        con.execute("CREATE TABLE users (id INTEGER PRIMARY KEY, username TEXT)")
    log_service.DB_PATH = str(log_db)


def test_logs_page_allows_blank_user_id(tmp_path):
    setup_in_memory_db()
    setup_log_db(tmp_path)
    app = create_app()
    with TestClient(app) as client:
        resp = client.get("/logs/records?log_type=inventory&user_id=")
        assert resp.status_code == 200
