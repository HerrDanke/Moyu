from __future__ import annotations

import threading

from sqlalchemy import select

from app.db import create_engine_for, create_session_factory, init_db
from app.models import Book, Chapter
from app.services import store

from .conftest import make_settings


def test_concurrent_read_write_no_lock_error(tmp_path):
    settings = make_settings(tmp_path)
    engine = create_engine_for(settings)
    init_db(engine)
    factory = create_session_factory(engine)

    setup = factory()
    book = Book(title="并发书", total_chapters=1)
    setup.add(book)
    setup.flush()
    setup.add(Chapter(book_id=book.id, index_no=1, title="第一章", content="内容" * 100, char_count=200))
    setup.commit()
    book_id = book.id
    setup.close()

    errors: list[Exception] = []

    def reader():
        s = factory()
        try:
            for _ in range(30):
                s.scalars(select(Chapter)).all()
        except Exception as exc:  # noqa: BLE001
            errors.append(exc)
        finally:
            s.close()

    def writer():
        s = factory()
        try:
            for i in range(30):
                store.write_progress(s, book_id, 1, i)
        except Exception as exc:  # noqa: BLE001
            errors.append(exc)
        finally:
            s.close()

    threads = [threading.Thread(target=reader) for _ in range(3)]
    threads += [threading.Thread(target=writer) for _ in range(2)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert errors == [], f"并发读写出现错误: {errors}"