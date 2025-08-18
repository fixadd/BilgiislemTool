import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from starlette.middleware.sessions import SessionMiddleware

import models
from routes.hardware import router as hardware_router
from routes.inventory import router as inventory_router
from routes.inventory_pages import router as inventory_pages_router
from utils.auth import require_login


def create_app():
    app = FastAPI()
    app.add_middleware(SessionMiddleware, secret_key="test")
    app.include_router(hardware_router, prefix="/hardware")
    app.include_router(inventory_router)
    app.include_router(inventory_pages_router)
    # Bypass authentication for tests
    app.dependency_overrides[require_login] = lambda: None
    return app


def setup_in_memory_db():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    models.engine = engine
    models.SessionLocal = TestingSessionLocal
    models.Base.metadata.create_all(bind=engine)


def test_hardware_router_lists_added_items():
    setup_in_memory_db()
    app = create_app()
    with TestClient(app) as client:
        resp = client.post(
            "/hardware/add",
            data={"no": "001", "donanim_tipi": "Laptop"},
            follow_redirects=False,
        )
        assert resp.status_code == 303
        resp = client.get("/hardware")
        assert resp.status_code == 200
        assert "Laptop" in resp.text


def test_stock_router_lists_added_items():
    setup_in_memory_db()
    app = create_app()
    with TestClient(app) as client:
        resp = client.post(
            "/stock/add", data={"urun_adi": "Mouse", "adet": "5"}, follow_redirects=False
        )
        assert resp.status_code == 303
        resp = client.get("/stock")
        assert resp.status_code == 200
        assert "Mouse" in resp.text


def test_accessories_router_lists_added_items():
    setup_in_memory_db()
    app = create_app()
    with TestClient(app) as client:
        resp = client.post(
            "/accessories/add", data={"urun_adi": "Kablo", "adet": "3"}, follow_redirects=False
        )
        assert resp.status_code == 303
        resp = client.get("/accessories")
        assert resp.status_code == 200
        assert "Kablo" in resp.text


def test_printer_router_lists_added_items_with_inventory_no():
    setup_in_memory_db()
    app = create_app()
    with TestClient(app) as client:
        resp = client.post(
            "/printer/add",
            data={
                "envanter_no": "P001",
                "yazici_markasi": "HP",
                "yazici_modeli": "LaserJet",
                "kullanim_alani": "Depo",
            },
            follow_redirects=False,
        )
        assert resp.status_code == 303
        resp = client.get("/printer")
        assert resp.status_code == 200
        assert "P001" in resp.text


def test_printer_upload_route_removed():
    setup_in_memory_db()
    app = create_app()
    with TestClient(app) as client:
        resp = client.post("/printer/upload")
        assert resp.status_code == 404


def test_inventory_upload_route_removed():
    setup_in_memory_db()
    app = create_app()
    with TestClient(app) as client:
        resp = client.post("/inventory/upload")
        assert resp.status_code == 404
