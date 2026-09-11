from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import create_app

from .conftest import make_settings


def _client(tmp_path, password):
    settings = make_settings(tmp_path, access_password=password)
    return TestClient(create_app(settings))


def test_protected_when_not_logged_in(tmp_path):
    client = _client(tmp_path, "secret")
    assert client.get("/api/books").status_code == 401
    assert client.get("/api/health").status_code == 200


def test_login_wrong_password(tmp_path):
    client = _client(tmp_path, "secret")
    resp = client.post("/api/auth/login", json={"password": "nope"})
    assert resp.status_code == 401


def test_login_then_access(tmp_path):
    client = _client(tmp_path, "secret")
    resp = client.post("/api/auth/login", json={"password": "secret"})
    assert resp.status_code == 200
    assert client.get("/api/books").status_code == 200
    status = client.get("/api/auth/status").json()
    assert status["authenticated"] is True


def test_no_password_configured_is_open(tmp_path):
    client = _client(tmp_path, "")
    assert client.get("/api/books").status_code == 200