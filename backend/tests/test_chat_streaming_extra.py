from __future__ import annotations

import json

from .conftest import import_sample


def _events(body: str) -> list[dict]:
    events = []
    for line in body.splitlines():
        line = line.strip()
        if not line.startswith("data:"):
            continue
        payload = line[5:].strip()
        if payload == "[DONE]":
            continue
        events.append(json.loads(payload))
    return events


def test_quick_read_sends_few_chunks(client):
    import_sample(client)
    resp = client.post("/api/chat", json={"message": "下一章", "quick_read": True})
    assert resp.status_code == 200
    events = _events(resp.text)
    chunks = [e for e in events if e["type"] == "chunk"]
    # 快速阅读：只演开头三段 + 其余一次送达
    assert 1 <= len(chunks) <= 4
    assert "青石阶" in "".join(c["text"] for c in chunks)


def test_meta_event_carries_chapter_geometry(client):
    import_sample(client)
    events = _events(client.post("/api/chat", json={"message": "下一章"}).text)
    meta = next(e for e in events if e["type"] == "meta")
    assert meta["chapter_index"] == 1
    assert meta["start_offset"] == 0
    assert meta["char_count"] > 0


def test_book_event_emitted(client):
    import_sample(client)
    events = _events(client.post("/api/chat", json={"message": "下一章"}).text)
    book = next(e for e in events if e["type"] == "book")
    assert book["id"] == 1


def test_switch_book_emits_that_book(client):
    import_sample(client)
    import_sample(client, name="another.txt")
    # 读第一本书
    client.post("/api/chat", json={"message": "读《sample》"})
    events = _events(client.post("/api/chat", json={"message": "读《another》"}).text)
    book = next(e for e in events if e["type"] == "book")
    assert book["id"] == 2


def test_text_response_has_no_meta(client):
    import_sample(client)
    events = _events(client.post("/api/chat", json={"message": "帮助"}).text)
    assert all(e["type"] != "meta" for e in events)