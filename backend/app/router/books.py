"""书目管理：导入 / 书单 / 详情 / 章节目录 / 删除。"""
from __future__ import annotations

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import Settings
from ..deps import get_app_settings, get_db, require_session
from ..models import Book, Chapter
from ..schemas import BookOut, ChapterMeta, ImportResult
from ..services.importer import ImporterError, import_book

router = APIRouter(
    prefix="/api/books", tags=["books"], dependencies=[Depends(require_session)]
)


@router.post("/import", response_model=ImportResult)
async def import_(
    file: UploadFile = File(...),
    session: Session = Depends(get_db),
    settings: Settings = Depends(get_app_settings),
):
    if file.size is not None and file.size > settings.max_upload_bytes:
        raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="文件超过大小上限")
    data = await file.read()
    try:
        book, notice = import_book(session, data, file.filename, settings)
    except ImporterError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return ImportResult(
        book_id=book.id,
        title=book.title,
        total_chapters=book.total_chapters,
        notice=notice,
    )


@router.get("", response_model=list[BookOut])
def list_books(session: Session = Depends(get_db)):
    books = session.scalars(select(Book).order_by(Book.id.asc())).all()
    return [BookOut.model_validate(b) for b in books]


@router.get("/{book_id}", response_model=BookOut)
def get_book(book_id: int, session: Session = Depends(get_db)):
    book = session.get(Book, book_id)
    if book is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="书不存在")
    return BookOut.model_validate(book)


@router.get("/{book_id}/chapters", response_model=list[ChapterMeta])
def list_chapters(book_id: int, session: Session = Depends(get_db)):
    if session.get(Book, book_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="书不存在")
    chapters = session.scalars(
        select(Chapter).where(Chapter.book_id == book_id).order_by(Chapter.index_no.asc())
    ).all()
    return [ChapterMeta(index_no=c.index_no, title=c.title, char_count=c.char_count) for c in chapters]


@router.delete("/{book_id}")
def delete_book(book_id: int, session: Session = Depends(get_db)):
    book = session.get(Book, book_id)
    if book is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="书不存在")
    session.delete(book)
    session.commit()
    return {"ok": True}