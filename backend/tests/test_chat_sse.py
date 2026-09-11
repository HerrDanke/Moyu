from __future__ import annotations

from .conftest import import_sample


def _chat(client, message: str) -> str:
    resp = client.post("/api/chat", json={"message": message})
    assert resp.status_code == 200
    assert "text/event-stream" in resp.headers["content-type"]
    return resp.text


def test_next_chapter_streams_and_advances(client):
    import_sample(client)
    body = _chat(client, "下一章")
    assert "data: " in body
    assert "初入江湖" in body  # 第一章标题
    assert "青石阶" in body  # 第一章正文
    assert "[DONE]" in body

    progress = client.get("/api/progress/1").json()
    assert progress["chapter_index"] == 1


def test_sequential_read(client):
    import_sample(client)
    _chat(client, "下一章")
    body2 = _chat(client, "下一章")
    assert "灵光乍现" in body2
    assert client.get("/api/progress/1").json()["chapter_index"] == 2


def test_last_chapter_notice(client):
    import_sample(client)
    _chat(client, "第 3 章")
    body = _chat(client, "下一章")
    assert "最新章节" in body
    # 进度仍在第 3 章
    assert client.get("/api/progress/1").json()["chapter_index"] == 3


def test_goto_out_of_range(client):
    import_sample(client)
    body = _chat(client, "第 99 章")
    assert "共 3 章" in body


def test_list_books_and_help_and_fallback(client):
    import_sample(client)
    assert "sample" in _chat(client, "书单")
    assert "下一章" in _chat(client, "帮助")
    assert "读书" in _chat(client, "今天天气不错")


def test_switch_book_and_search(client):
    import_sample(client)
    assert "初入江湖" in _chat(client, "读《sample》")
    assert "灵光乍现" in _chat(client, "搜 灵光")


def test_no_books_guides_user(client):
    body = _chat(client, "下一章")
    assert "导入" in body