import os
import sys

# Ensure project root is on sys.path
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

# Use a temporary SQLite database file for tests
test_db = os.path.join(os.path.dirname(__file__), "test.db")
if os.path.exists(test_db):
    os.remove(test_db)
os.environ["DATABASE_URL"] = f"sqlite:///{test_db}"

from fastapi.testclient import TestClient

import main
from models import init_db, SessionLocal, User, ActivityLog, pwd_context
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
    init_db()
    db = SessionLocal()
    db.add(User(username="ping_admin", password=pwd_context.hash("secret")))
    db.commit()
    db.close()

    client = TestClient(main.app)
    client.post(
        "/login", data={"username": "ping_admin", "password": "secret"}, follow_redirects=False
    )
    response = client.get("/ping")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_basic_pages():
    init_db()
    db = SessionLocal()
    db.add(User(username="admin", password=pwd_context.hash("secret")))
    db.commit()
    db.close()

    client = TestClient(main.app)
    login_resp = client.post(
        "/login", data={"username": "admin", "password": "secret"}, follow_redirects=False
    )
    assert login_resp.status_code == 303

    paths = [
        "/",
        "/stock",
        "/printer",
        "/home",
        "/inventory",
        "/license",
        "/accessories",
        "/requests",
        "/profile",
        "/lists",
    ]
    for path in paths:
        resp = client.get(path)
        assert resp.status_code == 200


def test_add_endpoints_exist():
    init_db()
    db = SessionLocal()
    db.add(User(username="admin2", password=pwd_context.hash("secret")))
    db.commit()
    db.close()

    client = TestClient(main.app)
    client.post(
        "/login", data={"username": "admin2", "password": "secret"}, follow_redirects=False
    )

    resp = client.post("/inventory/add", data={"no": "1"}, follow_redirects=False)
    assert resp.status_code == 303

    resp = client.post(
        "/license/add", data={"departman": "IT"}, follow_redirects=False
    )
    assert resp.status_code == 303

    resp = client.post(
        "/printer/add", data={"yazici_markasi": "HP"}, follow_redirects=False
    )
    assert resp.status_code == 303

    resp = client.post(
        "/inventory/upload",
        files={
            "excel_file": (
                "test.xlsx",
                b"data",
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
        },
        follow_redirects=False,
    )
    assert resp.status_code == 303
