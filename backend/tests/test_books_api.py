from __future__ import annotations

from .conftest import import_sample


def test_import_and_list(client):
    result = import_sample(client)
    assert result["total_chapters"] == 3
    assert result["notice"] is None

    books = client.get("/api/books").json()
    assert len(books) == 1
    assert books[0]["total_chapters"] == 3


def test_get_book_and_chapters(client):
    book_id = import_sample(client)["book_id"]
    detail = client.get(f"/api/books/{book_id}").json()
    assert detail["id"] == book_id

    chapters = client.get(f"/api/books/{book_id}/chapters").json()
    assert [c["index_no"] for c in chapters] == [1, 2, 3]
    assert "初入江湖" in chapters[0]["title"]


def test_delete_book_cascades(client, app):
    from sqlalchemy import select

    from app.models import Chapter

    book_id = import_sample(client)["book_id"]
    resp = client.delete(f"/api/books/{book_id}")
    assert resp.status_code == 200
    assert client.get(f"/api/books/{book_id}").status_code == 404
    assert client.get("/api/books").json() == []
    # 级联删除章节（依赖 PRAGMA foreign_keys=ON）
    session = app.state.session_factory()
    remaining = session.scalars(select(Chapter).where(Chapter.book_id == book_id)).all()
    session.close()
    assert remaining == []


def test_import_unknown_book_404(client):
    assert client.get("/api/books/9999").status_code == 404


def test_search_returns_hits(client):
    import_sample(client)
    resp = client.get("/api/search", params={"q": "灵光"})
    assert resp.status_code == 200
    hits = resp.json()["hits"]
    assert len(hits) == 1
    assert hits[0]["chapter_index"] == 2


def test_search_no_hit_returns_empty(client):
    import_sample(client)
    resp = client.get("/api/search", params={"q": "不存在的关键词"})
    assert resp.status_code == 200
    assert resp.json()["hits"] == []


def test_search_injection_safe(client):
    import_sample(client)
    resp = client.get("/api/search", params={"q": "%' OR 1=1 --"})
    assert resp.status_code == 200
    assert resp.json()["hits"] == []