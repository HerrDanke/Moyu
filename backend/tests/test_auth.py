from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import create_app
from app.security import create_session_token, set_setup_code

from .conftest import ADMIN_PASSWORD, create_user, make_settings


def _set_code(code: str = "TEST-CODE-1234-5678") -> str:
    set_setup_code(code)
    return code


def test_no_users_blocks_everything_but_bootstrap(tmp_path):
    """未初始化期间不得暴露任何数据。"""
    app = create_app(make_settings(tmp_path))
    client = TestClient(app)

    assert client.get("/api/books").status_code == 401
    assert client.get("/api/progress/1").status_code == 401
    assert client.get("/api/search").status_code == 401

    status = client.get("/api/auth/status")
    assert status.status_code == 200
    assert status.json()["setup_required"] is True
    # 状态接口绝不返回引导口令
    assert "setup_code" not in status.text


def test_login_success_and_failure(client, anon_client):
    assert anon_client.get("/api/books").status_code == 401

    bad = anon_client.post(
        "/api/auth/login", json={"username": "admin", "password": "wrong-password"}
    )
    assert bad.status_code == 401
    assert bad.json()["detail"] == "用户名或密码错误"

    unknown = anon_client.post(
        "/api/auth/login", json={"username": "nobody", "password": "whatever"}
    )
    assert unknown.status_code == 401
    # 不区分「用户不存在」与「密码错误」
    assert unknown.json()["detail"] == bad.json()["detail"]

    me = client.get("/api/auth/me")
    assert me.status_code == 200
    assert me.json()["username"] == "admin"
    assert me.json()["is_admin"] is True


def test_cannot_disable_self(client, admin_id):
    resp = client.patch(f"/api/users/{admin_id}", json={"is_active": False})
    assert resp.status_code == 400


def test_disabled_user_cannot_login(client, other_id, anon_client):
    assert client.patch(f"/api/users/{other_id}", json={"is_active": False}).status_code == 200
    resp = anon_client.post(
        "/api/auth/login", json={"username": "reader", "password": "other-pass-1234"}
    )
    assert resp.status_code == 401


def test_legacy_cookie_is_rejected(tmp_path):
    app = create_app(make_settings(tmp_path))
    create_user(app, "admin", ADMIN_PASSWORD, is_admin=True)
    client = TestClient(app)
    client.cookies.set("moyu_session", "Im9rIjp0cnVlfQ.aBcD.efGh")
    assert client.get("/api/books").status_code == 401


def test_password_change_revokes_existing_session(client, other_id, app):
    old = TestClient(app)
    old.post("/api/auth/login", json={"username": "reader", "password": "other-pass-1234"})
    assert old.get("/api/books").status_code == 200

    resp = client.patch(f"/api/users/{other_id}", json={"password": "brand-new-pass-9"})
    assert resp.status_code == 200

    # 旧会话立即失效
    assert old.get("/api/books").status_code == 401


def test_setup_flow(tmp_path):
    app = create_app(make_settings(tmp_path))
    client = TestClient(app)
    code = _set_code()

    wrong = client.post(
        "/api/auth/setup",
        json={"username": "boss", "password": "boss-pass-123", "setup_code": "NOPE"},
    )
    assert wrong.status_code == 401

    short = client.post(
        "/api/auth/setup",
        json={"username": "boss", "password": "abc", "setup_code": code},
    )
    assert short.status_code == 400

    bad_name = client.post(
        "/api/auth/setup",
        json={"username": "a b", "password": "boss-pass-123", "setup_code": code},
    )
    assert bad_name.status_code == 400

    ok = client.post(
        "/api/auth/setup",
        json={"username": "boss", "password": "boss-pass-123", "setup_code": code},
    )
    assert ok.status_code == 200
    assert ok.json()["is_admin"] is True
    # 引导成功即拿到会话
    assert client.get("/api/books").status_code == 200

    # 引导接口永久关闭
    again = client.post(
        "/api/auth/setup",
        json={"username": "boss2", "password": "boss-pass-456", "setup_code": code},
    )
    assert again.status_code == 409


def test_weak_secret_is_rejected_once_users_exist(tmp_path):
    app = create_app(make_settings(tmp_path))
    create_user(app, "admin", ADMIN_PASSWORD, is_admin=True)

    weak = make_settings(tmp_path, secret_key="dev-secret-change-me")
    try:
        create_app(weak)
    except RuntimeError:
        return
    raise AssertionError("存在用户时使用默认弱密钥应当拒绝启动")


def test_weak_secret_blocks_first_setup(tmp_path):
    """弱密钥下不允许完成引导，否则会留下一个会话可被伪造的系统。"""
    app = create_app(make_settings(tmp_path, secret_key="changeme"))
    client = TestClient(app)
    code = _set_code()
    resp = client.post(
        "/api/auth/setup",
        json={"username": "boss", "password": "boss-pass-123", "setup_code": code},
    )
    assert resp.status_code == 400


def test_password_stored_hashed(client, app):
    from sqlalchemy import select

    from app.models import User

    session = app.state.session_factory()
    user = session.scalar(select(User))
    assert user is not None
    assert user.password_hash.startswith(("scrypt$", "pbkdf2$"))
    assert ADMIN_PASSWORD not in user.password_hash
    session.close()


def test_session_token_roundtrip():
    from app.security import read_session_token

    token = create_session_token("k" * 40, 5, 2)
    assert read_session_token("k" * 40, token) == (5, 2)
    assert read_session_token("other-key", token) is None