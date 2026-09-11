"""数据库连接与初始化。

关键决策（评审 blocker）：
- WAL 日志模式：读不阻塞写，适配 SSE 长连接并发读 + 进度写入
- busy_timeout：写锁竞争时等待而非立即报 database is locked
- check_same_thread=False：SQLite 连接跨线程（FastAPI 线程池）
- foreign_keys=ON：级联删除依赖外键约束
"""
from __future__ import annotations

import sqlite3
from pathlib import Path

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from .config import Settings
from .models import Base


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


def init_db(engine: Engine) -> None:
    Base.metadata.create_all(engine)


def db_file_size(path: Path) -> int:
    try:
        return path.stat().st_size
    except OSError:
        return 0