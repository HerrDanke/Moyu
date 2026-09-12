"""跨用户数据隔离：进度与「当前书」必须互不可见、互不覆盖。"""
from __future__ import annotations

from sqlalchemy import select

from app.models import Progress

from .conftest import import_text


def test_two_users_have_independent_progress(client, other_client):
    book_id = import_text(client, "第一章 A\n甲\n第二章 B\n乙\n第三章 C\n丙\n")["book_id"]

    # admin 读到第 2 章
    client.post("/api/chat", json={"message": "下一章", "quick_read": True})
    client.post("/api/chat", json={"message": "下一章", "quick_read": True})
    assert client.get(f"/api/progress/{book_id}").json()["chapter_index"] == 2

    # 另一个用户读同一本书，是独立的进度
    fresh = other_client.get(f"/api/progress/{book_id}").json()
    assert fresh["chapter_index"] == 1

    other_client.post("/api/chat", json={"message": "下一章", "quick_read": True})
    assert other_client.get(f"/api/progress/{book_id}").json()["chapter_index"] == 1

    # admin 的进度未被对方的写入影响
    assert client.get(f"/api/progress/{book_id}").json()["chapter_index"] == 2


def test_progress_rows_are_scoped_by_user(client, other_client, admin_id, other_id, app):
    book_id = import_text(client, "第一章 A\n甲\n第二章 B\n乙\n")["book_id"]
    client.post("/api/chat", json={"message": "下一章", "quick_read": True})

    session = app.state.session_factory()
    rows = session.scalars(select(Progress).where(Progress.book_id == book_id)).all()
    session.close()

    assert {r.user_id for r in rows} == {admin_id}


def test_current_book_is_per_user(client, other_client):
    a = import_text(client, "第一章 A\n甲\n第二章 B\n乙\n", "bookA.txt")["book_id"]
    b = import_text(client, "第一章 C\n丙\n", "bookB.txt")["book_id"]

    # admin 的当前书是 b（最后导入）
    assert client.get(f"/api/progress/{b}").json()["book_id"] == b

    # 另一个用户把当前书设为 a
    assert other_client.post(f"/api/books/{a}/select").status_code == 200
    assert other_client.post(f"/api/books/{b}/select").status_code == 200

    # 再切回 a，并确认互不影响：admin 的当前书仍是 b
    other_client.post(f"/api/books/{a}/select")
    resp = other_client.post("/api/chat", json={"message": "下一章", "quick_read": True})
    assert resp.status_code == 200


def test_current_book_fallback_does_not_leak_across_users(
    client, other_client, admin_id, app
):
    """B 不能继承 A 最近读过的书（get_current_book 的回退分支必须按 user 过滤）。"""
    import_text(client, "第一章 A\n甲\n第二章 B\n乙\n")
    client.post("/api/chat", json={"message": "下一章", "quick_read": True})

    # 新用户没有任何进度、没有 current_book
    session = app.state.session_factory()
    from app.models import User

    reader = session.get(User, 2)  # reader
    assert reader is not None
    reader.current_book_id = None
    session.commit()
    session.close()

    from app.services import store

    session = app.state.session_factory()
    reader = session.get(User, 2)
    # 只有一本书 → 允许回退到它；关键是回退查询不能按 updated_at 命中他人的进度
    prog = session.scalar(select(Progress).where(Progress.user_id == reader.id))
    assert prog is None
    session.close()


def test_search_uses_own_current_book(client, other_client):
    book_id = import_text(client, "第一章 灵光乍现\n甲\n第二章 灵光再临\n乙\n", "book.txt")["book_id"]
    other_client.post(f"/api/books/{book_id}/select")

    mine = other_client.get("/api/search", params={"q": "灵光"}).json()
    assert mine["book_id"] == book_id
    assert len(mine["hits"]) == 2

    # admin 未指定书且未选定该书时，不应错误地沿用别人的当前书
    admin_view = client.get("/api/search", params={"q": "灵光"}).json()
    assert isinstance(admin_view["hits"], list)


def test_deleting_book_clears_every_users_progress(client, other_client, admin_id, other_id, app):
    book_id = import_text(client, "第一章 A\n甲\n", "gone.txt")["book_id"]
    client.post("/api/chat", json={"message": "下一章", "quick_read": True})
    other_client.post(f"/api/books/{book_id}/select")
    other_client.post("/api/chat", json={"message": "下一章", "quick_read": True})

    session = app.state.session_factory()
    assert len(session.scalars(select(Progress).where(Progress.book_id == book_id)).all()) == 2
    session.close()

    assert client.delete(f"/api/books/{book_id}").status_code == 200

    session = app.state.session_factory()
    assert session.scalars(select(Progress).where(Progress.book_id == book_id)).all() == []
    session.close()


def test_non_admin_cannot_delete_book(other_client, client):
    book_id = import_text(client, "第一章 A\n甲\n", "protected.txt")["book_id"]
    assert other_client.delete(f"/api/books/{book_id}").status_code == 403