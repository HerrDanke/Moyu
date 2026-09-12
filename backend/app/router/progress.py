"""阅读进度读写（按当前登录用户隔离）。"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..deps import get_db, require_session
from ..models import Book, Chapter, User
from ..schemas import ProgressOut, ProgressUpdate
from ..services import store

router = APIRouter(prefix="/api/progress", tags=["progress"])


def _max_chapter_index(session: Session, book_id: int) -> int:
    return (
        session.scalar(select(func.max(Chapter.index_no)).where(Chapter.book_id == book_id))
        or 0
    )


@router.get("/{book_id}", response_model=ProgressOut)
def get_progress(
    book_id: int,
    session: Session = Depends(get_db),
    user: User = Depends(require_session),
):
    book = session.get(Book, book_id)
    if book is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="书不存在")
    progress = store.get_progress(session, user.id, book_id)
    if progress is None:
        # 该用户尚未读过这本书：视为第一章开头
        return ProgressOut(
            user_id=user.id,
            book_id=book_id,
            chapter_index=1,
            chapter_offset=0,
            updated_at=book.created_at,
        )
    return ProgressOut.model_validate(progress)


@router.patch("/{book_id}", response_model=ProgressOut)
def patch_progress(
    book_id: int,
    payload: ProgressUpdate,
    session: Session = Depends(get_db),
    user: User = Depends(require_session),
):
    if session.get(Book, book_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="书不存在")

    current = store.get_progress(session, user.id, book_id)
    if payload.chapter_index is not None:
        chapter_index = payload.chapter_index
        max_index = _max_chapter_index(session, book_id)
        if max_index and (chapter_index < 1 or chapter_index > max_index):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"章节超出范围，本书共 {max_index} 章",
            )
    else:
        chapter_index = current.chapter_index if current else 1

    chapter_offset = (
        payload.chapter_offset
        if payload.chapter_offset is not None
        else (current.chapter_offset if current else 0)
    )
    store.write_progress(session, user.id, book_id, chapter_index, chapter_offset)
    return ProgressOut.model_validate(store.get_progress(session, user.id, book_id))