"""章节推进不得被静默丢弃。

历史缺陷（用户报告「目录跳到第 9 章后，点下一章回到第 3 章」）：
`write_progress` 用条件更新（乐观锁）做推进，当「旧章号」这个假设过期时
（同一行还会被前端的偏移上报 PATCH 并发写入），CAS 会匹配 0 行并**静默返回 False**，
于是用户看到了新章节的正文、进度却停在上一个章号，下一次「下一章」就跳错。
"""
from __future__ import annotations

from app.services import store

from .conftest import import_sample


def test_advance_wins_even_if_previous_value_is_stale(client, admin_id, app):
    book_id = import_sample(client)["book_id"]
    session = app.state.session_factory()

    store.write_progress(session, admin_id, book_id, 2, 0)
    # 模拟：本地以为旧值是 2，但期间同一行被别的写入改成了别的章号
    store.write_progress(session, admin_id, book_id, 5, 0)

    # 推进方带着过期的假设（from=2）来写第 9 章
    ok = store.write_progress(session, admin_id, book_id, 9, 0, conditional_from=2)

    current = store.get_progress(session, admin_id, book_id)
    session.close()

    assert ok is True, "推进不应被静默丢弃"
    assert current.chapter_index == 9, "用户已看到第 9 章，进度就应当是 9"


def test_advance_still_works_in_normal_case(client, admin_id, app):
    book_id = import_sample(client)["book_id"]
    session = app.state.session_factory()
    store.write_progress(session, admin_id, book_id, 2, 0)
    assert store.write_progress(session, admin_id, book_id, 3, 0, conditional_from=2) is True
    assert store.get_progress(session, admin_id, book_id).chapter_index == 3
    session.close()


def test_offset_patch_never_changes_chapter(client, admin_id, app):
    """偏移上报只应改 offset，绝不能动章号。"""
    book_id = import_sample(client)["book_id"]
    session = app.state.session_factory()
    store.write_progress(session, admin_id, book_id, 7, 0)

    client.patch(f"/api/progress/{book_id}", json={"chapter_offset": 1234})

    row = store.get_progress(session, admin_id, book_id)
    session.close()
    assert row.chapter_index == 7
    assert row.chapter_offset == 1234