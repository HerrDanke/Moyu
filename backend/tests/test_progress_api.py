from __future__ import annotations

from app.models import Progress
from app.services import store

from .conftest import import_sample


def test_default_progress_is_first_chapter(client):
    book_id = import_sample(client)["book_id"]
    resp = client.get(f"/api/progress/{book_id}").json()
    assert resp["chapter_index"] == 1
    assert resp["chapter_offset"] == 0


def test_patch_progress(client):
    book_id = import_sample(client)["book_id"]
    resp = client.patch(
        f"/api/progress/{book_id}", json={"chapter_index": 2, "chapter_offset": 10}
    ).json()
    assert resp["chapter_index"] == 2
    assert resp["chapter_offset"] == 10


def test_write_progress_optimistic_lock(client, app):
    book_id = import_sample(client)["book_id"]
    session = app.state.session_factory()
    store.write_progress(session, book_id, 2, 0)
    # 条件不匹配则跳过
    ok = store.write_progress(session, book_id, 3, 0, conditional_from=1)
    assert ok is False
    progress = session.get(Progress, book_id)
    assert progress.chapter_index == 2
    # 条件匹配则写入
    ok2 = store.write_progress(session, book_id, 3, 0, conditional_from=2)
    assert ok2 is True
    session.close()