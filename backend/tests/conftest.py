"""测试夹具：临时目录 + 独立 app 实例 + TestClient。"""
from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app

SAMPLE_TXT = """第一章 初入江湖

夜色如墨，韩立站在青石阶前，望着那巍峨的山门。
灵光流转，一道玉符悬于半空。

第二章 灵光乍现

晨光微露，他睁开眼，发现体内多了一缕灵气。
那道青芒顺着经脉游走，暖意融融。

第三章 山雨欲来

乌压压的云层压了下来，风中带着腥气。
他知道，真正的考验才刚刚开始。
"""


def make_settings(tmp_path: Path, **overrides) -> Settings:
    base = dict(
        data_dir=tmp_path / "data",
        novel_dir=tmp_path / "novels",
        static_dir=tmp_path / "static",
        typing_speed=0.0,  # 测试中不节流
        thinking_delay=0.0,
        access_password="",
        secret_key="test-secret",
    )
    base.update(overrides)
    return Settings(**base)


@pytest.fixture
def settings(tmp_path):
    return make_settings(tmp_path)


@pytest.fixture
def app(settings):
    return create_app(settings)


@pytest.fixture
def client(app):
    return TestClient(app)


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