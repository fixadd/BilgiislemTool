import os
import sys

# Reuse the helper and DB setup from test_app
sys.path.append(os.path.dirname(__file__))
from test_app import create_user  # noqa: E402

from fastapi.testclient import TestClient
import main  # noqa: E402


def test_trash_page_accessible_after_login():
    create_user()
    with TestClient(main.app) as client:
        client.post(
            "/login",
            data={"username": "tester", "password": "secret"},
            follow_redirects=False,
        )
        resp = client.get("/trash")
        assert resp.status_code == 200
