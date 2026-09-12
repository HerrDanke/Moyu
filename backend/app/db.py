"""数据库连接、初始化与老库迁移。

关键决策（评审 blocker）：
- WAL 日志模式：读不阻塞写，适配 SSE 长连接并发读 + 进度写入
- busy_timeout：写锁竞争时等待而非立即报 database is locked
- check_same_thread=False：SQLite 连接跨线程（FastAPI 线程池）
- foreign_keys=ON：级联删除依赖外键约束

迁移策略（引入账号体系）：
SQLite 不支持改主键，且 `create_all` 只能建缺失的表。因此把老的
`progress`（主键 book_id）改名为 `progress_legacy`，让 create_all 建出新结构，
待首个管理员创建成功后再把数据回填并 DROP 旧表。
"""
from __future__ import annotations

import sqlite3

from sqlalchemy import create_engine, event, func, select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from .config import Settings
from .models import Base, Progress, User


def _apply_pragmas(dbapi_conn: sqlite3.Connection, _record) -> None:
    cur = dbapi_conn.cursor()
    cur.execute("PRAGMA journal_mode=WAL")
    cur.execute("PRAGMA busy_timeout=5000")
    cur.execute("PRAGMA foreign_keys=ON")
    cur.execute("PRAGMA synchronous=NORMAL")
    cur.close()


def create_engine_for(settings: Settings) -> Engine:
    settings.ensure_dirs()
    url = f"sqlite:///{settings.db_path.as_posix()}"
    engine = create_engine(
        url,
        future=True,
        connect_args={"check_same_thread": False},
    )
    event.listen(engine, "connect", _apply_pragmas)
    return engine


def create_session_factory(engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(bind=engine, autoflush=False, expire_on_commit=False, future=True)


def _table_names(conn) -> set[str]:
    return {
        row[0]
        for row in conn.exec_driver_sql(
            "SELECT name FROM sqlite_master WHERE type='table'"
        )
    }


def _column_names(conn, table: str) -> set[str]:
    return {row[1] for row in conn.exec_driver_sql(f"PRAGMA table_info({table})")}


def _rename_legacy_progress(engine: Engine) -> bool:
    """老库的 progress 没有 user_id 列 → 改名，等 create_all 建新表。幂等。"""
    renamed = False
    with engine.begin() as conn:
        tables = _table_names(conn)
        if "progress" in tables and "progress_legacy" not in tables:
            if "user_id" not in _column_names(conn, "progress"):
                conn.exec_driver_sql("ALTER TABLE progress RENAME TO progress_legacy")
                renamed = True
    return renamed


def _add_missing_columns(engine: Engine) -> None:
    """为已存在的旧表补列（create_all 不会改已存在的表）。"""
    with engine.begin() as conn:
        tables = _table_names(conn)
        if "books" in tables and "uploaded_by" not in _column_names(conn, "books"):
            conn.exec_driver_sql(
                "ALTER TABLE books ADD COLUMN uploaded_by INTEGER "
                "REFERENCES users(id) ON DELETE SET NULL"
            )


def init_db(engine: Engine) -> None:
    _rename_legacy_progress(engine)
    Base.metadata.create_all(engine)
    _add_missing_columns(engine)


def has_legacy_progress(engine: Engine) -> bool:
    with engine.begin() as conn:
        return "progress_legacy" in _table_names(conn)


def backfill_legacy_data(engine: Engine, user_id: int) -> int:
    """把老库的进度与「当前书」归给指定用户，然后删除 legacy 表。返回迁移行数。"""
    if not has_legacy_progress(engine):
        return 0
    moved = 0
    with engine.begin() as conn:
        rows = conn.exec_driver_sql(
            "SELECT book_id, chapter_index, chapter_offset, updated_at FROM progress_legacy"
        ).fetchall()
        for book_id, chapter_index, chapter_offset, updated_at in rows:
            conn.exec_driver_sql(
                "INSERT OR IGNORE INTO progress "
                "(user_id, book_id, chapter_index, chapter_offset, updated_at) "
                "VALUES (?, ?, ?, ?, ?)",
                (user_id, book_id, chapter_index, chapter_offset, updated_at),
            )
            moved += 1
        current = conn.exec_driver_sql(
            "SELECT value FROM settings WHERE key = 'current_book'"
        ).fetchone()
        if current and current[0]:
            try:
                conn.exec_driver_sql(
                    "UPDATE users SET current_book_id = ? WHERE id = ?",
                    (int(current[0]), user_id),
                )
            except (TypeError, ValueError):
                pass
        conn.exec_driver_sql("DROP TABLE progress_legacy")
    return moved


def count_users(session: Session) -> int:
    return session.scalar(select(func.count(User.id))) or 0


def default_progress(session: Session, user_id: int, book_id: int) -> Progress:
    return session.get(Progress, (user_id, book_id))