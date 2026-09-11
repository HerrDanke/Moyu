"""章节标题搜索（参数化 LIKE，无注入面）。"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..deps import get_db, require_session
from ..models import Chapter
from ..schemas import SearchHit, SearchResult
from ..services import store

router = APIRouter(
    prefix="/api/search", tags=["search"], dependencies=[Depends(require_session)]
)


@router.get("", response_model=SearchResult)
def search(
    q: str = Query(default="", max_length=200),
    book_id: int | None = Query(default=None),
    session: Session = Depends(get_db),
):
    keyword = (q or "").strip()
    if not keyword:
        return SearchResult(book_id=book_id, query=q, hits=[])
    target_id = book_id
    if target_id is None:
        book = store.get_current_book(session)
        target_id = book.id if book else None
    if target_id is None:
        return SearchResult(book_id=None, query=q, hits=[])
    # 参数化绑定：keyword 仅作为绑定参数传入，不做字符串拼接
    chapters = session.scalars(
        select(Chapter)
        .where(Chapter.book_id == target_id, Chapter.title.like(f"%{keyword}%"))
        .order_by(Chapter.index_no.asc())
        .limit(50)
    ).all()
    hits = [SearchHit(chapter_index=c.index_no, title=c.title) for c in chapters]
    return SearchResult(book_id=target_id, query=q, hits=hits)