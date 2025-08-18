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
from models import SessionLocal, User, init_db, pwd_context, StockItem
import re


def create_user(username: str = "tester", password: str = "secret", is_admin: bool = False):
    init_db()
    db = SessionLocal()
    user = db.query(User).filter_by(username=username).first()
    if user:
        user.password = pwd_context.hash(password)
        user.is_admin = is_admin
    else:
        db.add(
            User(
                username=username,
                password=pwd_context.hash(password),
                is_admin=is_admin,
            )
        )
    db.commit()
    db.close()


def get_csrf(client: TestClient) -> str:
    resp = client.get("/login")
    m = re.search('name="csrf_token" value="([^"]+)"', resp.text)
    assert m
    return m.group(1)


def test_protected_routes_require_login():
    create_user()
    with TestClient(main.app) as client:
        resp = client.get("/ping")
        assert resp.status_code == 401

        resp = client.get("/", headers={"accept": "text/html"}, follow_redirects=False)
        assert resp.status_code in {302, 303, 307}


def test_login_creates_session_and_logout_clears_it():
    create_user()
    with TestClient(main.app) as client:
        token = get_csrf(client)
        resp = client.post(
            "/login",
            data={"username": "tester", "password": "secret", "csrf_token": token},
            follow_redirects=False,
        )
        assert resp.status_code == 303

        resp = client.get("/ping")
        assert resp.status_code == 200

        resp = client.post("/logout", data={"csrf_token": token}, follow_redirects=False)
        assert resp.status_code == 303

        resp = client.get("/ping")
        assert resp.status_code == 401


def test_logout_via_get_request():
    """Users should also be able to log out via GET requests."""
    create_user()
    with TestClient(main.app) as client:
        token = get_csrf(client)
        client.post(
            "/login",
            data={"username": "tester", "password": "secret", "csrf_token": token},
            follow_redirects=False,
        )
        resp = client.get("/ping")
        assert resp.status_code == 200

        resp = client.get("/logout", follow_redirects=False)
        assert resp.status_code == 303

        resp = client.get("/ping")
        assert resp.status_code == 401


def test_admin_routes_require_admin():
    create_user("admin_user", is_admin=True)
    create_user("normal_user", password="secret2", is_admin=False)
    with TestClient(main.app) as client:
        # non-admin should get forbidden
        token = get_csrf(client)
        client.post(
            "/login",
            data={"username": "normal_user", "password": "secret2", "csrf_token": token},
            follow_redirects=False,
        )
        resp = client.get("/admin", follow_redirects=False)
        assert resp.status_code == 403

        # switch to admin
        client.post("/logout", data={"csrf_token": token}, follow_redirects=False)
        token = get_csrf(client)
        client.post(
            "/login",
            data={"username": "admin_user", "password": "secret", "csrf_token": token},
            follow_redirects=False,
        )
        resp = client.get("/admin")
        assert resp.status_code == 200


def test_admin_can_create_user():
    create_user("site_admin", is_admin=True)
    with TestClient(main.app) as client:
        token = get_csrf(client)
        client.post(
            "/login",
            data={"username": "site_admin", "password": "secret", "csrf_token": token},
            follow_redirects=False,
        )

        resp = client.post(
            "/admin/create",
            data={"username": "new_user", "password": "pass"},
            follow_redirects=False,
        )
        assert resp.status_code == 303

    db = SessionLocal()
    try:
        assert db.query(User).filter_by(username="new_user").first() is not None
    finally:
        db.close()


def test_connections_route_requires_admin():
    create_user("conn_admin", is_admin=True)
    create_user("conn_user", password="pass2", is_admin=False)
    with TestClient(main.app) as client:
        token = get_csrf(client)
        client.post(
            "/login",
            data={"username": "conn_user", "password": "pass2", "csrf_token": token},
            follow_redirects=False,
        )
        resp = client.get("/connections", follow_redirects=False)
        assert resp.status_code == 403

        client.post("/logout", data={"csrf_token": token}, follow_redirects=False)
        token = get_csrf(client)
        client.post(
            "/login",
            data={"username": "conn_admin", "password": "secret", "csrf_token": token},
            follow_redirects=False,
        )
        resp = client.get("/connections")
    assert resp.status_code == 200


def test_stock_multiple_filters():
    create_user()
    db = SessionLocal()
    try:
        db.add(StockItem(urun_adi="Item1", kategori="cat1", marka="brand1", adet=1))
        db.add(StockItem(urun_adi="Item2", kategori="cat1", marka="brand2", adet=1))
        db.commit()
    finally:
        db.close()
    with TestClient(main.app) as client:
        token = get_csrf(client)
        client.post(
            "/login",
            data={"username": "tester", "password": "secret", "csrf_token": token},
            follow_redirects=False,
        )
        resp = client.get(
            "/stock",
            params=[
                ("filter_field", "kategori"),
                ("filter_value", "cat1"),
                ("filter_field", "marka"),
                ("filter_value", "brand1"),
            ],
        )
        assert resp.status_code == 200
        assert "Item1" in resp.text
        assert "Item2" not in resp.text


def test_change_password_flow():
    create_user()
    with TestClient(main.app) as client:
        token = get_csrf(client)
        client.post(
            "/login",
            data={"username": "tester", "password": "secret", "csrf_token": token},
            follow_redirects=False,
        )
        resp = client.get("/change-password")
        assert resp.status_code == 200
        token = re.search('name="csrf_token" value="([^"]+)"', resp.text).group(1)

        resp = client.post(
            "/change-password",
            data={
                "old_password": "secret",
                "new_password": "newpass",
                "confirm_password": "newpass",
                "csrf_token": token,
            },
            follow_redirects=False,
        )
        assert resp.status_code == 303

        client.post("/logout", data={"csrf_token": token}, follow_redirects=False)
        token = get_csrf(client)
        resp = client.post(
            "/login",
            data={"username": "tester", "password": "secret", "csrf_token": token},
            follow_redirects=False,
        )
        assert resp.status_code == 401

        token = get_csrf(client)
        resp = client.post(
            "/login",
            data={"username": "tester", "password": "newpass", "csrf_token": token},
            follow_redirects=False,
        )
        assert resp.status_code == 303
