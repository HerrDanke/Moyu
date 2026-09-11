"""settings 键值存储 + 「当前书」解析。"""
from __future__ import annotations

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..models import Book, Progress, Setting

CURRENT_BOOK_KEY = "current_book"


def get_setting(session: Session, key: str, default: str | None = None) -> str | None:
    row = session.get(Setting, key)
    return row.value if row is not None else default


def set_setting(session: Session, key: str, value: str) -> None:
    row = session.get(Setting, key)
    if row is None:
        session.add(Setting(key=key, value=value))
    else:
        row.value = value
    session.commit()


def set_current_book(session: Session, book_id: int) -> None:
    set_setting(session, CURRENT_BOOK_KEY, str(book_id))


def get_current_book(session: Session) -> Book | None:
    """当前书 = 显式选定的书 → 最近有进度的书 → 唯一的一本书。"""
    raw = get_setting(session, CURRENT_BOOK_KEY)
    if raw:
        try:
            book = session.get(Book, int(raw))
            if book is not None:
                return book
        except ValueError:
            pass
    prog = (
        session.query(Progress)
        .order_by(Progress.updated_at.desc())
        .first()
    )
    if prog is not None:
        book = session.get(Book, prog.book_id)
        if book is not None:
            return book
    books = session.query(Book).order_by(Book.id.asc()).all()
    if len(books) == 1:
        return books[0]
    return None


def write_progress(
    session: Session,
    book_id: int,
    chapter_index: int,
    offset: int = 0,
    *,
    conditional_from: int | None = None,
) -> bool:
    """写阅读进度。conditional_from 非空时做乐观锁：当前值不匹配则跳过写入。"""
    existing = session.get(Progress, book_id)
    if existing is None:
        try:
            session.add(
                Progress(book_id=book_id, chapter_index=chapter_index, chapter_offset=offset)
            )
            session.commit()
            return True
        except IntegrityError:
            # 并发下另一个会话已插入同一本书的进度，转为更新
            session.rollback()
            existing = session.get(Progress, book_id)
    if existing is None:
        return False
    if conditional_from is not None and existing.chapter_index != conditional_from:
        return False
    existing.chapter_index = chapter_index
    existing.chapter_offset = offset
    session.commit()
    return True