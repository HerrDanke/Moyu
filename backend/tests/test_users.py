from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import create_app

from .conftest import ADMIN_PASSWORD, OTHER_PASSWORD, create_user, login, make_settings


def test_non_admin_is_forbidden(other_client):
    assert other_client.get("/api/users").status_code == 403
    assert other_client.post(
        "/api/users", json={"username": "x1", "password": "password-123"}
    ).status_code == 403
    assert other_client.delete("/api/users/1").status_code == 403


def test_list_users_hides_hashes(client):
    users = client.get("/api/users").json()
    assert {u["username"] for u in users} >= {"admin"}
    assert all("password_hash" not in u for u in users)


def test_create_user_and_duplicate(client, anon_client):
    created = client.post(
        "/api/users", json={"username": "newbie", "password": "newbie-pass-1"}
    )
    assert created.status_code == 201
    assert created.json()["is_admin"] is False

    dup = client.post(
        "/api/users", json={"username": "newbie", "password": "newbie-pass-2"}
    )
    assert dup.status_code == 409

    # 新用户可立即登录
    fresh = TestClient(client.app)
    login(fresh, "newbie", "newbie-pass-1")
    assert fresh.get("/api/books").status_code == 200


def test_create_user_validation(client):
    assert client.post(
        "/api/users", json={"username": "ab", "password": "password-123"}
    ).status_code == 400
    assert client.post(
        "/api/users", json={"username": "has space", "password": "password-123"}
    ).status_code == 400
    assert client.post(
        "/api/users", json={"username": "okname", "password": "short"}
    ).status_code == 400


def test_cannot_remove_last_admin(client, admin_id):
    # 降级
    assert client.patch(f"/api/users/{admin_id}", json={"is_admin": False}).status_code == 400
    # 停用
    assert client.patch(f"/api/users/{admin_id}", json={"is_active": False}).status_code == 400
    # 删除
    assert client.delete(f"/api/users/{admin_id}").status_code == 400


def test_can_demote_when_another_admin_exists(client, other_id):
    assert client.patch(f"/api/users/{other_id}", json={"is_admin": True}).status_code == 200
    # 现在有两个管理员，可以降级其中一个（非自己）
    assert client.patch(f"/api/users/{other_id}", json={"is_admin": False}).status_code == 200


def test_delete_user_clears_progress_but_keeps_books(client, other_client, other_id, app):
    from sqlalchemy import select

    from app.models import Progress

    # 造一本书并用 second user 读一章
    resp = other_client.post(
        "/api/books/import",
        files={"file": ("t.txt", "第一章 A\n正文\n".encode(), "text/plain")},
    )
    book_id = resp.json()["book_id"]
    other_client.post("/api/chat", json={"message": "下一章", "quick_read": True})

    session = app.state.session_factory()
    assert session.scalar(select(Progress).where(Progress.user_id == other_id)) is not None
    session.close()

    assert client.delete(f"/api/users/{other_id}").status_code == 200

    session = app.state.session_factory()
    assert session.scalar(select(Progress).where(Progress.user_id == other_id)) is None
    session.close()
    # 书还在
    assert client.get(f"/api/books/{book_id}").status_code == 200


def test_update_ignores_unknown_fields(client, other_id):
    """字段白名单：username 之类的字段不应被 UserUpdate 接受。"""
    resp = client.patch(
        f"/api/users/{other_id}", json={"username": "hacked", "is_admin": False}
    )
    assert resp.status_code == 200
    assert resp.json()["username"] == "reader"


def test_admin_flag_comes_from_db_not_cookie(tmp_path, admin_id_unused=None):
    """普通用户即使自己签发 Cookie 指向管理员 id，也不能获得管理员权限。"""
    settings = make_settings(tmp_path)
    app = create_app(settings)
    create_user(app, "boss", ADMIN_PASSWORD, is_admin=True)
    uid = create_user(app, "plain", OTHER_PASSWORD, is_admin=False)

    from app.security import create_session_token

    client = TestClient(app)
    # 用自己的密钥签一个指向自己 id 的合法会话
    token = create_session_token(settings.secret_key, uid, 0)
    client.cookies.set("moyu_session", token)
    assert client.get("/api/auth/me").json()["is_admin"] is False
    assert client.get("/api/users").status_code == 403