import os
import sys

# Ensure project root is on sys.path
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

# Use a temporary SQLite database file for tests
TEST_DB = os.path.join(os.path.dirname(__file__), "test.db")
if os.path.exists(TEST_DB):
    os.remove(TEST_DB)
os.environ["DATABASE_URL"] = f"sqlite:///{TEST_DB}"

from fastapi.testclient import TestClient

import main
from models import SessionLocal, User, init_db, pwd_context


def create_user(username: str = "tester", password: str = "secret"):
    init_db()
    db = SessionLocal()
    if not db.query(User).filter_by(username=username).first():
        db.add(User(username=username, password=pwd_context.hash(password)))
        db.commit()
    db.close()


def test_protected_routes_require_login():
    create_user()
    client = TestClient(main.app)

    resp = client.get("/ping")
    assert resp.status_code == 401

    resp = client.get("/", headers={"accept": "text/html"}, follow_redirects=False)
    assert resp.status_code in {302, 303, 307}


def test_login_creates_session_and_logout_clears_it():
    create_user()
    client = TestClient(main.app)

    resp = client.post(
        "/login", data={"username": "tester", "password": "secret"}, follow_redirects=False
    )
    assert resp.status_code == 303

    resp = client.get("/ping")
    assert resp.status_code == 200

    resp = client.post("/logout", follow_redirects=False)
    assert resp.status_code == 303

    resp = client.get("/ping")
    assert resp.status_code == 401
