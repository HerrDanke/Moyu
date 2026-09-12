"""每用户设置与「思考强度」。"""
from __future__ import annotations

from app.services.user_settings import THINKING_LEVELS, level_for_speed, speed_for_level

from .conftest import import_sample


def test_defaults_fall_back_to_server_value(client):
    """未设置过的用户：速度来自环境变量带来的默认值。"""
    body = client.get("/api/settings").json()
    assert body["typing_speed_from_user"] is False
    assert body["typing_speed"] == 0.0  # 测试环境把 typing_speed 设为 0（不节流）
    assert len(body["levels"]) == 4


def test_set_and_persist_per_user(client, other_client):
    resp = client.patch("/api/settings", json={"typing_speed": 0.6})
    assert resp.status_code == 200
    assert resp.json()["typing_speed"] == 0.6
    assert resp.json()["typing_speed_from_user"] is True
    assert resp.json()["thinking_level"] == 3  # 深入

    # 同一用户再读，仍然生效
    assert client.get("/api/settings").json()["typing_speed"] == 0.6

    # 另一个用户不受影响
    other = other_client.get("/api/settings").json()
    assert other["typing_speed_from_user"] is False
    assert other["typing_speed"] != 0.6


def test_invalid_speed_rejected(client):
    for bad in (0, -1, 0.05, 100):
        resp = client.patch("/api/settings", json={"typing_speed": bad})
        assert resp.status_code == 400, f"{bad} 应被拒绝"
    # 之前的合法值没有被破坏
    client.patch("/api/settings", json={"typing_speed": 2.0})
    assert client.patch("/api/settings", json={"typing_speed": 0}).status_code == 400
    assert client.get("/api/settings").json()["typing_speed"] == 2.0


def test_level_mapping_is_consistent():
    for lv in THINKING_LEVELS:
        assert speed_for_level(lv.level) == lv.speed
        assert level_for_speed(lv.speed) == lv.level
    assert level_for_speed(1.234) is None


def test_user_pacing_reaches_chat(client, admin_id, app):
    """设置的速度要真的进到本次流式的配置里。"""
    from app.services.user_settings import with_user_pacing

    session = app.state.session_factory()
    from app.models import User

    user = session.get(User, admin_id)
    client.patch("/api/settings", json={"typing_speed": 0.35})

    base = app.state.settings
    effective = with_user_pacing(base, session, user)
    session.close()
    assert effective.typing_speed == 0.35
    # 原配置对象不被就地修改
    assert base.typing_speed == 0.0


def test_setting_does_not_break_reading(client):
    """设了速度之后，阅读流程仍然正常（含进度推进）。"""
    book_id = import_sample(client)["book_id"]
    client.patch("/api/settings", json={"typing_speed": 2.0})
    resp = client.post("/api/chat", json={"message": "下一章", "quick_read": True})
    assert resp.status_code == 200
    assert "[DONE]" in resp.text
    assert client.get(f"/api/progress/{book_id}").json()["chapter_index"] == 1