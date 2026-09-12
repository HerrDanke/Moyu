"""测试夹具：临时目录 + 独立 app 实例 + 已登录的 TestClient。

账号体系下大多数用例都需要登录态，因此 `client` 默认是**已登录的管理员**；
需要「未登录」时用 `anon_client`，需要「第二个用户」时用 `other_client`。
"""
from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app
from app.models import User
from app.security import hash_password
from app.services.ratelimit import reset_rate_limits

SAMPLE_TXT = """第一章 初入江湖

夜色如墨，韩立站在青石阶前，望着那巍峨的山门。
灵光流转，一道玉符悬于半空。

第二章 灵光乍现

晨光微露，他睁开眼，发现体内多了一缕灵气。

第三章 山雨欲来

乌压压的云层压了下来，风中带着腥气。
他知道，真正的考验才刚刚开始。
"""

ADMIN_PASSWORD = "admin-pass-1234"
OTHER_PASSWORD = "other-pass-1234"


def make_settings(tmp_path: Path, **overrides) -> Settings:
    base = dict(
        data_dir=tmp_path / "data",
        novel_dir=tmp_path / "novels",
        static_dir=tmp_path / "static",
        typing_speed=0.0,  # 测试中不节流
        thinking_delay=0.0,
        # 注意：必须是「非弱」密钥，否则存在用户时会拒绝启动
        secret_key="test-secret-key-with-sufficient-entropy",
    )
    base.update(overrides)
    return Settings(**base)


def create_user(app, username: str, password: str, *, is_admin: bool = False) -> int:
    session = app.state.session_factory()
    user = User(
        username=username,
        password_hash=hash_password(password),
        is_admin=is_admin,
        is_active=True,
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    user_id = user.id
    session.close()
    return user_id


def login(client: TestClient, username: str, password: str) -> TestClient:
    resp = client.post("/api/auth/login", json={"username": username, "password": password})
    assert resp.status_code == 200, resp.text
    return client


@pytest.fixture(autouse=True)
def _reset_rate_limits():
    """限速是全局状态，测试之间必须隔离，否则令牌桶会被跑空。"""
    reset_rate_limits()
    yield
    reset_rate_limits()


@pytest.fixture
def settings(tmp_path):
    return make_settings(tmp_path)


@pytest.fixture
def app(settings):
    return create_app(settings)


@pytest.fixture
def anon_client(app):
    """未登录客户端。"""
    return TestClient(app)


@pytest.fixture
def admin_id(app) -> int:
    return create_user(app, "admin", ADMIN_PASSWORD, is_admin=True)


@pytest.fixture
def client(app, admin_id) -> TestClient:
    """已登录的管理员客户端（多数用例使用）。"""
    return login(TestClient(app), "admin", ADMIN_PASSWORD)


@pytest.fixture
def other_id(app, admin_id) -> int:
    return create_user(app, "reader", OTHER_PASSWORD, is_admin=False)


@pytest.fixture
def other_client(app, admin_id, other_id) -> TestClient:
    """第二个用户（普通权限），用于验证数据隔离。"""
    return login(TestClient(app), "reader", OTHER_PASSWORD)


@pytest.fixture
def sample_bytes() -> bytes:
    return SAMPLE_TXT.encode("utf-8")


def import_sample(client: TestClient, name: str = "sample.txt") -> dict:
    resp = client.post(
        "/api/books/import",
        files={"file": (name, SAMPLE_TXT.encode("utf-8"), "text/plain")},
    )
    assert resp.status_code == 200, resp.text
    return resp.json()


def import_text(client: TestClient, text: str, name: str = "sample.txt") -> dict:
    resp = client.post(
        "/api/books/import",
        files={"file": (name, text.encode("utf-8"), "text/plain")},
    )
    assert resp.status_code == 200, resp.text
    return resp.json()