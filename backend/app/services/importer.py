"""导入服务：解析 → 备份 → 原子落库，失败回滚并清理孤儿文件。"""
from __future__ import annotations

import uuid
from pathlib import Path

from sqlalchemy.orm import Session

from ..config import Settings
from ..models import Book, Chapter
from ..readers.base import BaseReader
from ..readers.txt_reader import TxtReader


class ImporterError(Exception):
    """导入失败（业务可预期错误）。"""


def sanitize_filename(filename: str | None) -> str:
    if not filename:
        return "unknown.txt"
    # 仅取基名，去掉任何路径分隔与制表
    base = Path(filename.replace("\\", "/")).name.strip()
    return base or "unknown.txt"


def _safe_target(novel_dir: Path, name: str) -> Path:
    target = (novel_dir / name).resolve()
    if not target.is_relative_to(novel_dir.resolve()):
        raise ImporterError("非法的文件路径")
    return target


def import_book(
    session: Session,
    data: bytes,
    filename: str | None,
    settings: Settings,
    uploaded_by: int | None = None,
    reader: BaseReader | None = None,
) -> tuple[Book, str | None]:
    """导入一本书，返回 (Book, 提示文案)。失败抛 ImporterError。"""
    if not data:
        raise ImporterError("文件为空")
    if len(data) > settings.max_upload_bytes:
        raise ImporterError("文件超过大小上限")

    reader = reader or TxtReader(
        max_chapter_chars=settings.max_chapter_chars,
        fallback_chapter_chars=settings.fallback_chapter_chars,
    )
    try:
        parsed = reader.read(data)
    except ValueError as exc:
        raise ImporterError(str(exc)) from exc

    if not parsed.chapters:
        raise ImporterError("未解析到任何章节内容")

    safe_name = sanitize_filename(filename)
    title = Path(safe_name).stem or safe_name

    # 先写原文备份，DB 失败时清理
    backup_name = f"{uuid.uuid4().hex}.txt"
    backup_path = _safe_target(settings.novel_dir, backup_name)
    backup_path.write_bytes(data)

    try:
        book = Book(
            title=title,
            source_filename=safe_name,
            total_chapters=len(parsed.chapters),
            uploaded_by=uploaded_by,
        )
        session.add(book)
        session.flush()  # 拿到 book.id
        for ch in parsed.chapters:
            session.add(
                Chapter(
                    book_id=book.id,
                    index_no=ch.index_no,
                    title=ch.title,
                    content=ch.content,
                    char_count=ch.char_count,
                )
            )
        session.commit()
    except Exception:
        session.rollback()
        # 清理备份，但不能掩盖原始异常
        try:
            backup_path.unlink(missing_ok=True)
        except OSError:
            pass
        raise

    notice = None
    if parsed.used_fallback:
        notice = "未识别到章节分隔，已按字数分段"
    return book, notice