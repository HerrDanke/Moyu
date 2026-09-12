from __future__ import annotations

from app.services import store

from .conftest import import_sample


def test_default_progress_is_first_chapter(client, admin_id):
    book_id = import_sample(client)["book_id"]
    resp = client.get(f"/api/progress/{book_id}").json()
    assert resp["user_id"] == admin_id
    assert resp["chapter_index"] == 1
    assert resp["chapter_offset"] == 0


def test_patch_progress(client):
    book_id = import_sample(client)["book_id"]
    resp = client.patch(
        f"/api/progress/{book_id}", json={"chapter_index": 2, "chapter_offset": 10}
    ).json()
    assert resp["chapter_index"] == 2
    assert resp["chapter_offset"] == 10


def test_out_of_range_chapter_rejected(client):
    book_id = import_sample(client)["book_id"]
    resp = client.patch(f"/api/progress/{book_id}", json={"chapter_index": 9999})
    assert resp.status_code == 400


def test_offset_only_update_keeps_chapter(client):
    book_id = import_sample(client)["book_id"]
    client.patch(f"/api/progress/{book_id}", json={"chapter_index": 2})
    resp = client.patch(f"/api/progress/{book_id}", json={"chapter_offset": 42}).json()
    assert resp["chapter_index"] == 2
    assert resp["chapter_offset"] == 42


def test_write_progress_atomic_cas(client, admin_id, app):
    book_id = import_sample(client)["book_id"]
    session = app.state.session_factory()
    store.write_progress(session, admin_id, book_id, 1, 0)
    # 旧值匹配 → 走 CAS 快路径推进成功
    assert store.write_progress(session, admin_id, book_id, 2, 0, conditional_from=1) is True
    assert store.get_progress(session, admin_id, book_id).chapter_index == 2

    # 旧值不匹配（假设过期）→ 仍然推进，绝不静默丢弃。
    # 语义变更说明：早期实现返回 False 且什么都不写，导致「用户已看到新章节、
    # 进度却停在上一个章号」，下一次「下一章」就跳错章。详见 test_progress_advance.py。
    assert store.write_progress(session, admin_id, book_id, 3, 0, conditional_from=1) is True
    assert store.get_progress(session, admin_id, book_id).chapter_index == 3
    session.close()


def test_progress_is_scoped_per_user(client, other_client, admin_id, app):
    book_id = import_sample(client)["book_id"]
    client.patch(f"/api/progress/{book_id}", json={"chapter_index": 2})

    # 另一个用户看到的是自己的默认进度，而不是别人的
    other = other_client.get(f"/api/progress/{book_id}").json()
    assert other["chapter_index"] == 1
    assert other["user_id"] != admin_id

    session = app.state.session_factory()
    assert store.get_progress(session, admin_id, book_id).chapter_index == 2
    session.close()