"""全局 settings 键值存储 + 「当前书」解析 + 阅读进度写入。

账号体系下「当前书」与阅读进度都是**用户级**的：
所有读写都必须带 `user_id`，否则会跨用户串数据。
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone

from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..models import Book, Progress, Setting, User

logger = logging.getLogger("moyu.store")


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


def set_current_book(session: Session, user: User, book_id: int) -> None:
    user.current_book_id = book_id
    session.commit()


def get_current_book(session: Session, user: User) -> Book | None:
    """当前书 = 该用户显式选定的书 → 该用户最近有进度的书 → 唯一的一本书。

    注意：回退分支必须按 user_id 过滤，否则 B 会「继承」A 最近读过的书。
    """
    if user.current_book_id is not None:
        book = session.get(Book, user.current_book_id)
        if book is not None:
            return book

    prog = session.scalar(
        select(Progress)
        .where(Progress.user_id == user.id)
        .order_by(Progress.updated_at.desc())
    )
    if prog is not None:
        book = session.get(Book, prog.book_id)
        if book is not None:
            return book

    books = session.scalars(select(Book).order_by(Book.id.asc())).all()
    if len(books) == 1:
        return books[0]
    return None


def get_progress(session: Session, user_id: int, book_id: int) -> Progress | None:
    return session.get(Progress, (user_id, book_id))


def write_progress(
    session: Session,
    user_id: int,
    book_id: int,
    chapter_index: int,
    offset: int = 0,
    *,
    conditional_from: int | None = None,
    require_row: bool = False,
) -> bool:
    """写阅读进度（用户级）。

    conditional_from 非空时会先尝试原子 CAS（UPDATE ... WHERE chapter_index = 旧值），
    以减少多标签页重复推进；**但 CAS 未命中时会退化为无条件写入**——
    章节推进代表用户已经看到了新章节的正文，绝不能因为「旧章号」这个假设过期
    就把整次推进静默丢掉（否则界面显示第 9 章、进度却停在第 2 章，
    下一次「下一章」会跳错章）。同一行还会被前端的偏移上报并发写入，
    这个窗口是真实存在的。
    """
    existing = session.get(Progress, (user_id, book_id))
    if existing is None:
        if require_row:
            return False
        try:
            session.add(
                Progress(
                    user_id=user_id,
                    book_id=book_id,
                    chapter_index=chapter_index,
                    chapter_offset=offset,
                )
            )
            session.commit()
            return True
        except IntegrityError:
            session.rollback()
            existing = session.get(Progress, (user_id, book_id))
        if existing is None:
            return False

    if conditional_from is not None:
        result = session.execute(
            update(Progress)
            .where(
                Progress.user_id == user_id,
                Progress.book_id == book_id,
                Progress.chapter_index == conditional_from,
            )
            .values(
                chapter_index=chapter_index,
                chapter_offset=offset,
                updated_at=datetime.now(timezone.utc),
            )
        )
        session.commit()
        if result.rowcount > 0:
            return True
        # CAS 未命中：说明「旧章号」假设已过期（例如前端的偏移上报并发改了同一行）。
        # 此时绝不能静默丢弃这次推进，退化为无条件写入。
        logger.warning(
            "progress CAS 未命中，退化为直接写入：user=%s book=%s from=%s to=%s",
            user_id,
            book_id,
            conditional_from,
            chapter_index,
        )
        session.expire_all()

    existing = session.get(Progress, (user_id, book_id))
    if existing is None:
        return False
    existing.chapter_index = chapter_index
    existing.chapter_offset = offset
    session.commit()
    return True


def clear_current_book_reference(session: Session, book_id: int) -> None:
    """书籍被删除时，清掉指向它的 users.current_book_id（该列无外键约束）。"""
    session.execute(
        update(User).where(User.current_book_id == book_id).values(current_book_id=None)
    )