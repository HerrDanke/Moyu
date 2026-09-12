"""SQLAlchemy 数据模型：users / books / chapters / progress / settings。

注意：`users.current_book_id` 有意**不加外键约束**——
users→books 与 books→users 会形成循环外键，SQLite 不支持 ALTER TABLE ADD CONSTRAINT，
建表时无法排序。删除书籍时在业务代码里显式清空该引用。
"""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def _now() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(32), unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    is_admin: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    # 会话版本号：改密 / 停用 / 删除时自增，用于吊销既有 Cookie
    token_version: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    # 该用户当前的「当前书」（无外键约束，见模块 docstring）
    current_book_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now, nullable=False)


class Book(Base):
    __tablename__ = "books"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(512), nullable=False)
    source_filename: Mapped[str] = mapped_column(String(512), nullable=False, default="")
    total_chapters: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    uploaded_by: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now, nullable=False)

    chapters: Mapped[list["Chapter"]] = relationship(
        back_populates="book",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class Chapter(Base):
    __tablename__ = "chapters"
    __table_args__ = (UniqueConstraint("book_id", "index_no", name="uq_chapter_book_index"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    book_id: Mapped[int] = mapped_column(
        ForeignKey("books.id", ondelete="CASCADE"), nullable=False, index=True
    )
    index_no: Mapped[int] = mapped_column(Integer, nullable=False)
    title: Mapped[str] = mapped_column(String(512), nullable=False, default="")
    content: Mapped[str] = mapped_column(Text, nullable=False, default="")
    char_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    book: Mapped[Book] = relationship(back_populates="chapters")


class Progress(Base):
    """每个用户、每本书一行。主键为 (user_id, book_id)。"""

    __tablename__ = "progress"

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    book_id: Mapped[int] = mapped_column(
        ForeignKey("books.id", ondelete="CASCADE"), primary_key=True
    )
    chapter_index: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    chapter_offset: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=_now, onupdate=_now, nullable=False
    )


class Setting(Base):
    """全局配置（非用户级）。当前书已迁到 users.current_book_id。"""

    __tablename__ = "settings"

    key: Mapped[str] = mapped_column(String(128), primary_key=True)
    value: Mapped[str] = mapped_column(Text, nullable=False, default="")


class UserSetting(Base):
    """每用户设置。键值表设计：新增设置项不必改表结构。"""

    __tablename__ = "user_settings"

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    key: Mapped[str] = mapped_column(String(64), primary_key=True)
    value: Mapped[str] = mapped_column(Text, nullable=False, default="")