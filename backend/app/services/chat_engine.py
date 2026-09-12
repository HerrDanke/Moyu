"""对话引擎：把用户输入解析为意图，并组装「伪 AI」回复计划。

所有文案均为本地模板生成，不调用任何外部服务。
"""
from __future__ import annotations

import re
from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..config import Settings
from ..models import Book, Chapter, User
from . import store

# 线性正则（无嵌套量词），配合输入截断避免 ReDoS
_RE_NEXT = re.compile(r"^\s*(下一章|下章|继续读|继续|再来(一章)?|next)\s*$", re.IGNORECASE)
_RE_PREV = re.compile(r"^\s*(上一章|上章|上一回|返回|往前|prev)\s*$", re.IGNORECASE)
# 从断点续读**本章**。注意：裸露的「继续」「继续读」已被上面的 _RE_NEXT 占用为「下一章」，
# 这是既有且被测试固化的行为，不要改动；这条正则靠锚定与它区分。
_RE_RESUME = re.compile(r"^\s*(继续本章|续读本章|接着读)\s*$")
_RE_GOTO = re.compile(r"第\s*(\d{1,6})\s*[章回节]|跳到\s*(\d{1,6})|到第\s*(\d{1,6})")
_RE_LIST = re.compile(r"^\s*(书单|书目|有哪些书|所有书|列表|书架)\s*$")
_RE_SWITCH = re.compile(r"^\s*(?:读|换书|打开|看)\s*[《<]?\s*(.+?)\s*[》>]?\s*$")
_RE_SEARCH = re.compile(r"^\s*(?:搜|搜索|查找|找|有)\s*(.+?)\s*(?:吗|么)?\s*$")
_RE_HELP = re.compile(r"^\s*(帮助|help|\?|？|你能干嘛|怎么用|使用说明)\s*$", re.IGNORECASE)


@dataclass
class Intent:
    kind: str  # next|prev|goto|resume|list_books|switch_book|search|help|fallback
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
    # 续读**不改变章号**，而章内偏移由前端实时上报，所以服务端不该在流结束后把
    # 「请求时刻读到的旧偏移」写回去——那会把用户真正读到的位置回滚
    # （极速档下打字机可能先跑完，这条陈旧写入就成了最后一次写入）。
    progress_skip_write: bool = False
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
    if _RE_RESUME.match(text):
        return Intent(kind="resume")
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
    "· 「继续本章」—— 从上次停下的地方接着读\n"
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
    skip_write: bool = False,
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
        progress_skip_write=skip_write,
        meta_chapter_index=chapter.index_no,
        meta_start_offset=start_offset,
        meta_char_count=len(chapter.content),
    )


def _get_chapter(session: Session, book_id: int, index_no: int) -> Chapter | None:
    return session.scalar(
        select(Chapter).where(Chapter.book_id == book_id, Chapter.index_no == index_no)
    )


def _no_book_response(session: Session) -> ChatResponse:
    total = session.scalar(select(func.count(Book.id))) or 0
    if total == 0:
        return _text_response(
            "你好，我还没看到你的藏书。先点左侧「导入新书」把一本 TXT 小说导入进来，我们就能开始读了。"
        )
    return _text_response("想读哪本书？回复『书单』看看收藏。")


def build_response(
    session: Session, settings: Settings, message: str, user: User
) -> ChatResponse:
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
        store.set_current_book(session, user, book.id)
        prog = store.get_progress(session, user.id, book.id)
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
        book = store.get_current_book(session, user)
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

    # next / prev / goto / resume 需要当前书
    book = store.get_current_book(session, user)
    if book is None:
        return _no_book_response(session)

    prog = store.get_progress(session, user.id, book.id)
    current = prog.chapter_index if prog else 0
    prev_index = prog.chapter_index if prog else None
    max_index = session.scalar(
        select(func.max(Chapter.index_no)).where(Chapter.book_id == book.id)
    ) or 0

    if intent.kind == "resume":
        # 从断点续读**本章**：复用 _chapter_response(resume=True) 的取文与 meta 生成逻辑，
        # 因此流式分批与前端偏移上报的行为和「切书续读」完全一致。
        index = current or 1
        offset = prog.chapter_offset if prog else 0
        chapter = _get_chapter(session, book.id, index)
        if chapter is None:
            return _text_response(f"没找到第 {index} 章。")
        content_len = len(chapter.content)
        if content_len == 0 or offset >= content_len:
            # 刻意**不**沿用 _chapter_response 里「断点越界则回到开头」的兜底：
            # 手输「第 N 章」时从开头重放是合理的，但一个明确叫「继续本章」的按钮
            # 在已读完（或本章没有正文）时无声重放会让人困惑，所以明确告知。
            return _text_response(
                f"《{book.title}》第 {index} 章已经读完了，说「下一章」接着读吧。"
            )
        # skip_write：续读不改章号，章内偏移由前端实时上报；服务端不能在这里把
        # 「请求时刻的旧偏移」写回去，否则会回滚用户真正读到的位置。
        return _chapter_response(
            book, chapter, start_offset=offset, resume=True, skip_write=True
        )

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