"""书目管理：导入 / 书单 / 详情 / 章节目录 / 删除 / 选定当前书。

书库为**全体登录用户共享**；删除书籍需要管理员；「当前书」是用户级设置。
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.orm import Session
from starlette.concurrency import run_in_threadpool

from ..config import Settings
from ..deps import get_app_settings, get_db, require_admin, require_session
from ..models import Book, Chapter, User
from ..schemas import BookOut, ChapterMeta, ImportResult
from ..services import store
from ..services.importer import ImporterError, import_book

router = APIRouter(prefix="/api/books", tags=["books"])


def _to_out(session: Session, book: Book) -> BookOut:
    uploader = session.get(User, book.uploaded_by) if book.uploaded_by else None
    return BookOut(
        id=book.id,
        title=book.title,
        source_filename=book.source_filename,
        total_chapters=book.total_chapters,
        uploaded_by=book.uploaded_by,
        uploaded_by_name=uploader.username if uploader else None,
        created_at=book.created_at,
    )


@router.post("/import", response_model=ImportResult)
async def import_(
    file: UploadFile = File(...),
    session: Session = Depends(get_db),
    settings: Settings = Depends(get_app_settings),
    user: User = Depends(require_session),
):
    if file.size is not None and file.size > settings.max_upload_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="文件超过大小上限"
        )
    data = await file.read()
    if len(data) > settings.max_upload_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="文件超过大小上限"
        )
    try:
        # 解析与落库是阻塞操作，放到线程池，避免卡住正在进行的 SSE 流
        book, notice = await run_in_threadpool(
            import_book, session, data, file.filename, settings, user.id
        )
    except ImporterError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    # 导入者自动成为当前书
    store.set_current_book(session, user, book.id)
    return ImportResult(
        book_id=book.id,
        title=book.title,
        total_chapters=book.total_chapters,
        notice=notice,
    )


@router.get("", response_model=list[BookOut])
def list_books(session: Session = Depends(get_db), _user: User = Depends(require_session)):
    books = session.scalars(select(Book).order_by(Book.id.asc())).all()
    return [_to_out(session, b) for b in books]


@router.get("/{book_id}", response_model=BookOut)
def get_book(
    book_id: int, session: Session = Depends(get_db), _user: User = Depends(require_session)
):
    book = session.get(Book, book_id)
    if book is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="书不存在")
    return _to_out(session, book)


@router.get("/{book_id}/chapters", response_model=list[ChapterMeta])
def list_chapters(
    book_id: int, session: Session = Depends(get_db), _user: User = Depends(require_session)
):
    if session.get(Book, book_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="书不存在")
    chapters = session.scalars(
        select(Chapter).where(Chapter.book_id == book_id).order_by(Chapter.index_no.asc())
    ).all()
    return [
        ChapterMeta(index_no=c.index_no, title=c.title, char_count=c.char_count)
        for c in chapters
    ]


@router.post("/{book_id}/select")
def select_book(
    book_id: int,
    session: Session = Depends(get_db),
    user: User = Depends(require_session),
):
    """把某本书设为**当前用户自己**的「当前书」，不影响其他用户。"""
    if session.get(Book, book_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="书不存在")
    store.set_current_book(session, user, book_id)
    return {"ok": True, "book_id": book_id}


@router.delete("/{book_id}")
def delete_book(
    book_id: int,
    session: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
):
    """删除书籍需要管理员；会清掉所有用户在该书上的进度。"""
    book = session.get(Book, book_id)
    if book is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="书不存在")
    store.clear_current_book_reference(session, book_id)
    session.delete(book)
    session.commit()
    return {"ok": True}