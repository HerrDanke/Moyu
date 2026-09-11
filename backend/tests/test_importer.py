from __future__ import annotations

import pytest

from app.models import Book, Chapter
from app.readers.base import BaseReader, ParsedChapter, ParseResult
from app.services.importer import ImporterError, import_book, sanitize_filename

from .conftest import make_settings


class DuplicateIndexReader(BaseReader):
    """返回重复 index_no 的解析结果，用于触发唯一约束失败以验证回滚。"""

    def read(self, data: bytes) -> ParseResult:
        return ParseResult(
            chapters=[
                ParsedChapter(index_no=1, title="第一章", content="A"),
                ParsedChapter(index_no=1, title="第一章重复", content="B"),
            ],
            used_fallback=False,
            encoding="utf-8",
        )


def _session(settings):
    from app.db import create_engine_for, create_session_factory, init_db

    engine = create_engine_for(settings)
    init_db(engine)
    return create_session_factory(engine)()


def test_sanitize_filename():
    assert sanitize_filename("../../etc/passwd") == "passwd"
    assert sanitize_filename("C:\\novels\\a.txt") == "a.txt"
    assert sanitize_filename("") == "unknown.txt"


def test_import_success(tmp_path):
    settings = make_settings(tmp_path)
    session = _session(settings)
    book, notice = import_book(session, "第一章 开始\n正文内容\n".encode("utf-8"), "书.txt", settings)
    assert book.id is not None
    assert notice is None
    assert session.query(Chapter).filter_by(book_id=book.id).count() == 1
    # 原文备份写入
    assert len(list(settings.novel_dir.glob("*.txt"))) == 1


def test_import_fallback_notice(tmp_path):
    settings = make_settings(tmp_path)
    session = _session(settings)
    payload = ("没有章节标题的段落。" * 400).encode("utf-8")
    book, notice = import_book(session, payload, "无标题.txt", settings)
    assert notice is not None
    assert "字数分段" in notice


def test_import_rejects_empty(tmp_path):
    settings = make_settings(tmp_path)
    session = _session(settings)
    with pytest.raises(ImporterError):
        import_book(session, b"", "empty.txt", settings)


def test_import_rejects_oversize(tmp_path):
    settings = make_settings(tmp_path, max_upload_bytes=10)
    session = _session(settings)
    with pytest.raises(ImporterError):
        import_book(session, b"x" * 100, "big.txt", settings)


def test_import_rollback_cleans_backup(tmp_path):
    settings = make_settings(tmp_path)
    session = _session(settings)
    with pytest.raises(Exception):
        import_book(session, "第一章\nA".encode("utf-8"), "bad.txt", settings, reader=DuplicateIndexReader())
    # 无孤儿记录
    assert session.query(Book).count() == 0
    assert session.query(Chapter).count() == 0
    # 备份已清理
    assert list(settings.novel_dir.glob("*.txt")) == []