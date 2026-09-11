"""对话引擎：把用户输入解析为意图，并组装「伪 AI」回复计划。

所有文案均为本地模板生成，不调用任何外部服务。
"""
from __future__ import annotations

import re
from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..config import Settings
from ..models import Book, Chapter, Progress
from . import store

# 线性正则（无嵌套量词），配合输入截断避免 ReDoS
_RE_NEXT = re.compile(r"^\s*(下一章|下章|继续读|继续|再来(一章)?|next)\s*$", re.IGNORECASE)
_RE_PREV = re.compile(r"^\s*(上一章|上章|上一回|返回|往前|prev)\s*$", re.IGNORECASE)
_RE_GOTO = re.compile(r"第\s*(\d{1,6})\s*[章回节]|跳到\s*(\d{1,6})|到第\s*(\d{1,6})")
_RE_LIST = re.compile(r"^\s*(书单|书目|有哪些书|所有书|列表|书架)\s*$")
_RE_SWITCH = re.compile(r"^\s*(?:读|换书|打开|看)\s*[《<]?\s*(.+?)\s*[》>]?\s*$")
_RE_SEARCH = re.compile(r"^\s*(?:搜|搜索|查找|找|有)\s*(.+?)\s*(?:吗|么)?\s*$")
_RE_HELP = re.compile(r"^\s*(帮助|help|\?|？|你能干嘛|怎么用|使用说明)\s*$", re.IGNORECASE)


@dataclass
class Intent:
    kind: str  # next|prev|goto|list_books|switch_book|search|help|fallback
    number: int | None = None
    keyword: str | None = None


@dataclass
class ChatResponse:
    kind: str  # "chapter" | "text"
    thinking: str | None
    body: str
    title: str | None = None
    footer: str | None = None
    # —— 进度写入 ——
    progress_book_id: int | None = None
    progress_chapter_index: int | None = None
    progress_offset: int | None = None
    progress_prev_index: int | None = None
    # 章节推进用条件更新（CAS）；续读/跟读不做 CAS
    progress_conditional: bool = False
    # —— 章节元信息（前端据此计算续读字符偏移）——
    meta_chapter_index: int | None = None
    meta_start_offset: int = 0
    meta_char_count: int = 0


def parse_intent(message: str, max_chars: int = 500) -> Intent:
    text = (message or "").strip()[:max_chars]
    if not text:
        return Intent(kind="fallback")

    if _RE_NEXT.match(text):
        return Intent(kind="next")
    if _RE_PREV.match(text):
        return Intent(kind="prev")
    m = _RE_GOTO.search(text)
    if m:
        num = next((g for g in m.groups() if g), None)
        return Intent(kind="goto", number=int(num) if num else None)
    if _RE_LIST.match(text):
        return Intent(kind="list_books")
    if _RE_HELP.match(text):
        return Intent(kind="help")

    m = _RE_SWITCH.match(text)
    if m and len(m.group(1)) <= 200:
        return Intent(kind="switch_book", keyword=m.group(1).strip())
    m = _RE_SEARCH.match(text)
    if m and len(m.group(1)) <= 200:
        return Intent(kind="search", keyword=m.group(1).strip())
    return Intent(kind="fallback")


HELP_TEXT = (
    "我可以陪你一起读小说。你可以这样对我说：\n"
    "· 「下一章」/「上一章」—— 翻页\n"
    "· 「第 20 章」—— 跳到指定章节\n"
    "· 「书单」—— 看看收藏了哪些书\n"
    "· 「读《书名》」—— 换一本书\n"
    "· 「搜 关键词」—— 找找相关章节\n"
    "现在，试试对我说「下一章」吧。"
)


def _text_response(body: str) -> ChatResponse:
    return ChatResponse(kind="text", thinking=None, body=body, footer=None)


def _chapter_response(
    book: Book,
    chapter: Chapter,
    *,
    start_offset: int,
    resume: bool,
    prev_index: int | None = None,
) -> ChatResponse:
    # 断点超出正文范围时回到章节开头，避免续读为空
    if start_offset <= 0 or start_offset >= len(chapter.content):
        start_offset = 0
    body = chapter.content[start_offset:]
    thinking = f"正在为你加载《{book.title}》第 {chapter.index_no} 章…"
    footer = f"第 {chapter.index_no} 章完 · 回复『下一章』继续阅读"
    return ChatResponse(
        kind="chapter",
        thinking=thinking,
        body=body,
        title=chapter.title,
        footer=footer,
        progress_book_id=book.id,
        progress_chapter_index=chapter.index_no,
        progress_offset=start_offset if resume else 0,
        progress_prev_index=prev_index,
        progress_conditional=not resume,
        meta_chapter_index=chapter.index_no,
        meta_start_offset=start_offset,
        meta_char_count=len(chapter.content),
    )


def _get_chapter(session: Session, book_id: int, index_no: int) -> Chapter | None:
    return session.scalar(
        select(Chapter).where(Chapter.book_id == book_id, Chapter.index_no == index_no)
    )


def _progress(session: Session, book_id: int) -> Progress | None:
    return session.get(Progress, book_id)


def _no_book_response(session: Session) -> ChatResponse:
    total = session.scalar(select(func.count(Book.id))) or 0
    if total == 0:
        return _text_response(
            "你好，我还没看到你的藏书。先点右上角把一本 TXT 小说导入进来，我们就能开始读了。"
        )
    return _text_response("想读哪本书？回复『书单』看看收藏。")


def build_response(session: Session, settings: Settings, message: str) -> ChatResponse:
    intent = parse_intent(message, settings.max_input_chars)

    if intent.kind == "help":
        return _text_response(HELP_TEXT)
    if intent.kind == "fallback":
        return _text_response(
            "我主要帮你读书。说「下一章」继续、「上一章」回看，或说「书单」挑一本。"
        )
    if intent.kind == "list_books":
        books = session.scalars(select(Book).order_by(Book.id.asc())).all()
        if not books:
            return _no_book_response(session)
        lines = [f"《{b.title}》（共 {b.total_chapters} 章）" for b in books]
        return _text_response("你的书架：\n" + "\n".join(f"· {ln}" for ln in lines))

    if intent.kind == "switch_book":
        keyword = (intent.keyword or "").strip()
        book = session.scalar(
            select(Book).where(Book.title.like(f"%{escape_like(keyword)}%", escape="\\"))
        )
        if book is None:
            return _text_response(f"没找到叫「{keyword}」的书，回复『书单』看看有哪些吧。")
        store.set_current_book(session, book.id)
        prog = _progress(session, book.id)
        index = prog.chapter_index if prog else 1
        offset = prog.chapter_offset if prog else 0
        chapter = _get_chapter(session, book.id, index)
        if chapter is None:
            return _no_book_response(session)
        return _chapter_response(book, chapter, start_offset=offset, resume=True)

    if intent.kind == "search":
        keyword = (intent.keyword or "").strip()
        if not keyword:
            return _text_response("想搜什么？把关键词告诉我，比如「搜 韩立」。")
        book = store.get_current_book(session)
        if book is None:
            return _no_book_response(session)
        hits = session.scalars(
            select(Chapter)
            .where(
                Chapter.book_id == book.id,
                Chapter.title.like(f"%{escape_like(keyword)}%", escape="\\"),
            )
            .order_by(Chapter.index_no.asc())
            .limit(20)
        ).all()
        if not hits:
            return _text_response(f"在《{book.title}》里没找到跟「{keyword}」相关的章节。")
        lines = [f"· 第 {c.index_no} 章 {c.title}" for c in hits]
        return _text_response(
            f"在《{book.title}》里找到 {len(hits)} 个相关章节：\n" + "\n".join(lines)
        )

    # next / prev / goto 需要当前书
    book = store.get_current_book(session)
    if book is None:
        return _no_book_response(session)

    prog = _progress(session, book.id)
    current = prog.chapter_index if prog else 0
    prev_index = prog.chapter_index if prog else None
    max_index = session.scalar(
        select(func.max(Chapter.index_no)).where(Chapter.book_id == book.id)
    ) or 0

    if intent.kind == "next":
        target = (current + 1) if current else 1
        if current and target > max_index:
            return _text_response("已经是最新章节了，等更新吧～")
    elif intent.kind == "prev":
        if current <= 1:
            return _text_response("已经是第一章了，往前没有了。")
        target = current - 1
    else:  # goto
        num = intent.number or 0
        if num < 1 or num > max_index:
            return _text_response(f"《{book.title}》共 {max_index} 章，请输入 1~{max_index} 之间的章节。")
        target = num

    chapter = _get_chapter(session, book.id, target)
    if chapter is None:
        return _text_response(f"没找到第 {target} 章。")
    return _chapter_response(book, chapter, start_offset=0, resume=False, prev_index=prev_index)


def escape_like(text: str) -> str:
    """转义 LIKE 通配符，避免用户输入 % / _ 变成通配。"""
    return text.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")