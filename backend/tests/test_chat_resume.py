"""「继续本章」：从断点续读**本章**，而不是跳到下一章或从头重放。

补的历史空白：中途停下后，「下一章」会跳到下一章、「第 N 章」会从头重放，
会话内没有任何入口能接着读本章剩下的部分——只有刷新页面或切走再切回才会断点续读。
"""
from __future__ import annotations

import json

from sqlalchemy import select

from app.models import Progress, User
from app.services.chat_engine import build_response

from .conftest import import_text

RESUME_TXT = """第一章 断点测试

开头第一句。开头第二句在此。
中间第三句。中间第四句在此。
结尾第五句。结尾第六句在此。

第二章 第二章标题

第二章的正文第一句。第二章第二句。
"""


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


def _chat(client, message: str) -> list[dict]:
    resp = client.post("/api/chat", json={"message": message})
    assert resp.status_code == 200
    return _events(resp.text)


def _body(events: list[dict]) -> str:
    """把 chunk 事件拼回正文。

    标题与收尾文案走独立的 title/footer 事件，不在 chunk 里，
    因此这里拼出来的就是 `chapter.content[start_offset:]`。
    """
    return "".join(e["text"] for e in events if e["type"] == "chunk")


def _meta(events: list[dict]) -> dict:
    return next(e for e in events if e["type"] == "meta")


def _all_text(events: list[dict]) -> str:
    return "".join(e.get("text", "") for e in events)


def test_resume_sends_only_the_remainder(client):
    """核心语义：只送断点之后的剩余部分，已读部分不重放。"""
    import_text(client, RESUME_TXT)

    # 先完整读第 1 章拿到正文原文 —— 不依赖导入器对空白/换行的任何处理
    full = _body(_chat(client, "下一章"))
    assert "开头第一句" in full
    assert "结尾第六句" in full

    # 模拟「读到中段就离开」
    cut = full.index("中间第三句")
    assert 0 < cut < len(full)
    resp = client.patch("/api/progress/1", json={"chapter_index": 1, "chapter_offset": cut})
    assert resp.status_code == 200
    assert resp.json()["chapter_offset"] == cut

    events = _chat(client, "继续本章")
    body = _body(events)

    assert body == full[cut:]  # 正好是剩余部分
    assert body.startswith("中间第三句")
    assert "开头第一句" not in body  # 已读部分没有被重放

    meta = _meta(events)
    assert meta["chapter_index"] == 1  # 仍在本章，没有跳到第 2 章
    assert meta["start_offset"] == cut
    assert meta["char_count"] == len(full)

    # 续读把进度回落到断点（resume 路径不做章节推进 CAS，与切书续读一致）
    prog = client.get("/api/progress/1").json()
    assert prog["chapter_index"] == 1
    assert prog["chapter_offset"] == cut


def test_all_aliases_resume_from_the_same_offset(client):
    import_text(client, RESUME_TXT)
    _chat(client, "下一章")
    client.patch("/api/progress/1", json={"chapter_index": 1, "chapter_offset": 6})

    for phrase in ("继续本章", "续读本章", "接着读"):
        events = _chat(client, phrase)
        meta = _meta(events)
        assert meta["chapter_index"] == 1, phrase
        assert meta["start_offset"] == 6, phrase


def test_finished_chapter_notice_instead_of_replay(client):
    """本章读完后再按「继续本章」：明确告知，而不是无声重放整章。"""
    import_text(client, RESUME_TXT)
    full = _body(_chat(client, "下一章"))
    client.patch(
        "/api/progress/1", json={"chapter_index": 1, "chapter_offset": len(full)}
    )

    events = _chat(client, "继续本章")

    assert "已经读完了" in _all_text(events)
    assert "下一章" in _all_text(events)
    # 判定「这是文字回复而不是章节」要看 meta：正文一律走 chunk 事件（文字回复也一样），
    # 只有 kind == "chapter" 才会发 meta。没有 meta 说明没有重放章节。
    assert all(e["type"] != "meta" for e in events)


def test_resume_without_progress_starts_chapter_one(client):
    """没有任何进度时从第 1 章开头开始，不报错。"""
    import_text(client, RESUME_TXT)

    events = _chat(client, "继续本章")

    meta = _meta(events)
    assert meta["chapter_index"] == 1
    assert meta["start_offset"] == 0
    assert "开头第一句" in _body(events)


def test_resume_without_current_book_guides_user(client):
    """没有当前书时与「下一章」一致：引导去导入/选书。"""
    assert "导入" in _all_text(_chat(client, "继续本章"))


def test_lone_jixu_still_advances_to_next_chapter(client):
    """边界防回归：裸露的「继续」「继续读」仍是「下一章」，不能被 resume 抢走。"""
    import_text(client, RESUME_TXT)

    for phrase in ("继续", "继续读"):
        # 每轮都重置回第 1 章，否则第二轮会越界（样本只有 2 章）
        client.patch("/api/progress/1", json={"chapter_index": 1, "chapter_offset": 0})
        meta = _meta(_chat(client, phrase))
        assert meta["chapter_index"] == 2, phrase


def test_resume_alone_does_not_create_progress_row(client, app):
    """续读**不在服务端**写进度。

    这是「跳过写入」与「写回旧值」之间可观测的差异：旧实现会在流结束后调用
    write_progress，于是没有进度行时也会凭空创建出 (第 1 章, 偏移 0) 这一行。
    """
    import_text(client, RESUME_TXT)
    _chat(client, "继续本章")  # 没有进度行 → 从第 1 章开头读

    session = app.state.session_factory()
    try:
        assert session.scalars(select(Progress)).all() == []
    finally:
        session.close()


def test_resume_flags_skip_write_but_others_do_not(client, app):
    """续读必须显式声明「服务端不要写进度」，其余指令照常写。

    原因：续读不改章号，章内偏移由前端实时上报。服务端若把请求时刻读到的旧偏移
    写回去，会回滚用户真正读到的位置（极速档下打字机可能先跑完，这条陈旧写入
    就成了最后一次写入）。
    """
    import_text(client, RESUME_TXT)

    def build(message: str):
        session = app.state.session_factory()
        try:
            user = session.scalar(select(User).where(User.username == "admin"))
            return build_response(session, app.state.settings, message, user)
        finally:
            session.close()

    assert build("继续本章").progress_skip_write is True
    # 对照：翻页与跳章要负责推进章号，必须照常写入
    assert build("下一章").progress_skip_write is False
    assert build("第 2 章").progress_skip_write is False
