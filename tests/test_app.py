import os
import sys

# Ensure project root is on sys.path
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

# Use in-memory SQLite for tests
os.environ["DATABASE_URL"] = "sqlite:///:memory:"

from fastapi.testclient import TestClient

import main
from models import init_db, SessionLocal, User, ActivityLog
from utils import log_action


def test_log_action():
    init_db()
    db = SessionLocal()
    user = User(username="tester", password="pwd")
    db.add(user)
    db.commit()
    log_action(db, "tester", "created")
    assert db.query(User).count() == 1
    assert db.query(ActivityLog).count() == 1
    db.close()


def test_ping_route():
    client = TestClient(main.app)
    response = client.get("/ping")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_basic_pages():
    client = TestClient(main.app)
    for path in ["/", "/login", "/stock", "/printer"]:
        resp = client.get(path)
        assert resp.status_code == 200


def test_column_helper_endpoints():
    client = TestClient(main.app)

    resp = client.get("/column-settings", params={"table_name": "stock"})
    assert resp.status_code == 200
    assert resp.json() == {}

    payload = {"order": ["a"], "visible": ["a"], "widths": {"a": 100}}
    resp = client.post(
        "/column-settings",
        params={"table_name": "stock"},
        json=payload,
    )
    assert resp.status_code == 200
    assert resp.json() == payload

    resp = client.get("/table-columns", params={"table_name": "stock"})
    assert resp.status_code == 200
    assert resp.json() == {"columns": []}

    resp = client.get(
        "/column-values", params={"table_name": "stock", "column": "name"}
    )
    assert resp.status_code == 200
    assert resp.json() == []
