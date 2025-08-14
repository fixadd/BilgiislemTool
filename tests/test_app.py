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


def create_user(username: str = "tester", password: str = "secret", is_admin: bool = False):
    init_db()
    db = SessionLocal()
    if not db.query(User).filter_by(username=username).first():
        db.add(
            User(
                username=username,
                password=pwd_context.hash(password),
                is_admin=is_admin,
            )
        )
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


def test_admin_routes_require_admin():
    create_user("admin_user", is_admin=True)
    create_user("normal_user", password="secret2", is_admin=False)
    client = TestClient(main.app)

    # non-admin should get forbidden
    client.post(
        "/login", data={"username": "normal_user", "password": "secret2"}, follow_redirects=False
    )
    resp = client.get("/admin", follow_redirects=False)
    assert resp.status_code == 403

    # switch to admin
    client.post("/logout", follow_redirects=False)
    client.post(
        "/login", data={"username": "admin_user", "password": "secret"}, follow_redirects=False
    )
    resp = client.get("/admin")
    assert resp.status_code == 200


def test_admin_can_create_user():
    create_user("site_admin", is_admin=True)
    client = TestClient(main.app)
    client.post(
        "/login", data={"username": "site_admin", "password": "secret"}, follow_redirects=False
    )

    resp = client.post(
        "/admin/create", data={"username": "new_user", "password": "pass"}, follow_redirects=False
    )
    assert resp.status_code == 303

    db = SessionLocal()
    try:
        assert db.query(User).filter_by(username="new_user").first() is not None
    finally:
        db.close()
