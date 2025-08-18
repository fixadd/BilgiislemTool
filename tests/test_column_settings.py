import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(__file__)))

import models
import utils
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from starlette.middleware.sessions import SessionMiddleware

from routes.inventory_pages import router as inventory_pages_router
from utils.auth import require_login
from fastapi_csrf_protect import CsrfProtect
from pydantic_settings import BaseSettings


def create_app():
    app = FastAPI()
    app.add_middleware(SessionMiddleware, secret_key="test")
    app.include_router(inventory_pages_router)
    app.dependency_overrides[require_login] = lambda: None
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
    models.Base.metadata.create_all(bind=engine)


class CsrfSettings(BaseSettings):
    secret_key: str = "test-secret"
    token_key: str = "csrf_token"
    token_location: str = "body"


@CsrfProtect.load_config
def get_csrf_config() -> CsrfSettings:
    return CsrfSettings()


def test_save_and_load_column_settings(tmp_path):
    setup_in_memory_db()
    utils.SETTINGS_FILE = str(tmp_path / "settings.json")
    app = create_app()
    data_license = {"order": ["a"], "visible": ["a"], "widths": {"a": 100}}
    data_printer = {"order": ["b"], "visible": ["b"], "widths": {"b": 80}}
    with TestClient(app) as client:
        csrf = CsrfProtect()
        token, signed = csrf.generate_csrf_tokens()
        client.cookies.set("fastapi-csrf-token", signed)
        resp = client.post(
            "/column-settings?table_name=license", json={**data_license, "csrf_token": token}
        )
        assert resp.status_code == 200
        resp = client.get("/column-settings?table_name=license")
        assert resp.json() == data_license
        token, signed = csrf.generate_csrf_tokens()
        client.cookies.set("fastapi-csrf-token", signed)
        resp = client.post(
            "/column-settings?table_name=printer", json={**data_printer, "csrf_token": token}
        )
        assert resp.status_code == 200
        resp = client.get("/column-settings?table_name=printer")
        assert resp.json() == data_printer
