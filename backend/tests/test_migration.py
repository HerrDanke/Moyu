"""老库升级：把「每书一行」的 progress 迁移成「每用户每书一行」，并归给首个管理员。"""
from __future__ import annotations

import sqlite3

from fastapi.testclient import TestClient

from app.db import has_legacy_progress
from app.main import create_app
from app.security import set_setup_code

from .conftest import make_settings

LEGACY_SCHEMA = """
CREATE TABLE books (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  title VARCHAR(512) NOT NULL,
  source_filename VARCHAR(512) NOT NULL DEFAULT '',
  total_chapters INTEGER NOT NULL DEFAULT 0,
  created_at DATETIME NOT NULL
);
CREATE TABLE chapters (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  book_id INTEGER NOT NULL REFERENCES books(id) ON DELETE CASCADE,
  index_no INTEGER NOT NULL,
  title VARCHAR(512) NOT NULL DEFAULT '',
  content TEXT NOT NULL DEFAULT '',
  char_count INTEGER NOT NULL DEFAULT 0,
  UNIQUE (book_id, index_no)
);
CREATE TABLE progress (
  book_id INTEGER PRIMARY KEY,
  chapter_index INTEGER NOT NULL DEFAULT 1,
  chapter_offset INTEGER NOT NULL DEFAULT 0,
  updated_at DATETIME NOT NULL
);
CREATE TABLE settings (
  key VARCHAR(128) PRIMARY KEY,
  value TEXT NOT NULL DEFAULT ''
);
"""


def _make_legacy_db(settings) -> None:
    settings.ensure_dirs()
    conn = sqlite3.connect(settings.db_path)
    conn.executescript(LEGACY_SCHEMA)
    conn.execute(
        "INSERT INTO books (id, title, source_filename, total_chapters, created_at) "
        "VALUES (1, '宠魅', '宠魅.txt', 3, '2026-01-01 00:00:00')"
    )
    conn.execute(
        "INSERT INTO chapters (book_id, index_no, title, content, char_count) "
        "VALUES (1, 1, '第一章', '正文一', 3), (1, 2, '第二章', '正文二', 3)"
    )
    conn.execute(
        "INSERT INTO progress (book_id, chapter_index, chapter_offset, updated_at) "
        "VALUES (1, 2, 120, '2026-01-02 00:00:00')"
    )
    conn.execute("INSERT INTO settings (key, value) VALUES ('current_book', '1')")
    conn.commit()
    conn.close()


def test_legacy_progress_migrates_to_first_admin(tmp_path):
    settings = make_settings(tmp_path)
    _make_legacy_db(settings)

    app = create_app(settings)
    # 迁移第一步：老表已改名，等待回填
    assert has_legacy_progress(app.state.engine) is True

    client = TestClient(app)
    assert client.get("/api/auth/status").json()["setup_required"] is True

    set_setup_code("MIGRATE-CODE-0000")
    resp = client.post(
        "/api/auth/setup",
        json={"username": "boss", "password": "boss-pass-123", "setup_code": "MIGRATE-CODE-0000"},
    )
    assert resp.status_code == 200
    admin_id = resp.json()["id"]

    # 老进度归给首个管理员，且「当前书」一并继承
    progress = client.get("/api/progress/1").json()
    assert progress["user_id"] == admin_id
    assert progress["chapter_index"] == 2
    assert progress["chapter_offset"] == 120

    # legacy 表已删除，迁移不可重复触发
    assert has_legacy_progress(app.state.engine) is False

    # 书籍本体保留
    books = client.get("/api/books").json()
    assert len(books) == 1
    assert books[0]["title"] == "宠魅"


def test_migration_is_idempotent(tmp_path):
    settings = make_settings(tmp_path)
    _make_legacy_db(settings)

    app1 = create_app(settings)
    assert has_legacy_progress(app1.state.engine) is True
    # 再次启动不应报错、也不应重复改名
    app2 = create_app(settings)
    assert has_legacy_progress(app2.state.engine) is True
    assert app1.state.engine is not app2.state.engine


def test_fresh_install_has_no_legacy_table(tmp_path):
    app = create_app(make_settings(tmp_path))
    assert has_legacy_progress(app.state.engine) is False