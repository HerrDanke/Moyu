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


def test_search_wildcard_is_escaped(client):
    import_sample(client)
    # 单独的 % 不应作为通配符命中所有章节
    resp = client.get("/api/search", params={"q": "%"})
    assert resp.status_code == 200
    assert resp.json()["hits"] == []


def test_select_book_sets_current(client, admin_id, app):
    from app.models import User
    from app.services import store

    book_id = import_sample(client)["book_id"]
    resp = client.post(f"/api/books/{book_id}/select")
    assert resp.status_code == 200
    session = app.state.session_factory()
    user = session.get(User, admin_id)
    current = store.get_current_book(session, user)
    session.close()
    assert current is not None and current.id == book_id


def test_import_records_uploader(client, admin_id):
    import_sample(client)
    books = client.get("/api/books").json()
    assert books[0]["uploaded_by"] == admin_id
    assert books[0]["uploaded_by_name"] == "admin"


def test_delete_book_requires_admin(other_client, client):
    book_id = import_sample(client)["book_id"]
    assert other_client.delete(f"/api/books/{book_id}").status_code == 403
    assert client.delete(f"/api/books/{book_id}").status_code == 200


def test_unknown_api_path_is_404_not_html(tmp_path):
    # 必须挂载静态目录才能真正验证 SPA fallback 不会吞掉未注册的 /api/*
    from fastapi.testclient import TestClient

    from app.main import create_app

    from .conftest import make_settings

    static = tmp_path / "static"
    static.mkdir()
    (static / "index.html").write_text('<!doctype html><div id="root"></div>', "utf-8")
    app = create_app(make_settings(tmp_path, static_dir=static))
    client = TestClient(app)

    assert client.get("/api/does-not-exist").status_code == 404
    # 普通深层路由仍回退到 index.html
    resp = client.get("/some/deep/route")
    assert resp.status_code == 200 and 'id="root"' in resp.text