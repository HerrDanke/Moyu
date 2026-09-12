"""Pydantic 请求/响应模型。"""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from .security import PASSWORD_MAX_LENGTH


# --------------------------------------------------------------------------
# 账号
# --------------------------------------------------------------------------
class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=64)
    # 上限同时是抗 KDF 放大的措施
    password: str = Field(min_length=1, max_length=PASSWORD_MAX_LENGTH)


class SetupRequest(BaseModel):
    username: str = Field(min_length=1, max_length=64)
    password: str = Field(min_length=1, max_length=PASSWORD_MAX_LENGTH)
    setup_code: str = Field(min_length=1, max_length=128)


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    is_admin: bool
    is_active: bool
    created_at: datetime


class UserCreate(BaseModel):
    username: str = Field(min_length=1, max_length=64)
    password: str = Field(min_length=1, max_length=PASSWORD_MAX_LENGTH)
    is_admin: bool = False


class UserUpdate(BaseModel):
    """字段白名单：只允许改这三项，防止越权修改 is_admin 之外的字段。"""

    password: str | None = Field(default=None, min_length=1, max_length=PASSWORD_MAX_LENGTH)
    is_admin: bool | None = None
    is_active: bool | None = None


class AuthStatus(BaseModel):
    setup_required: bool
    authenticated: bool
    user: UserOut | None = None


# --------------------------------------------------------------------------
# 书籍
# --------------------------------------------------------------------------
class BookOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    source_filename: str
    total_chapters: int
    uploaded_by: int | None = None
    uploaded_by_name: str | None = None
    created_at: datetime


class ChapterMeta(BaseModel):
    index_no: int
    title: str
    char_count: int


class ImportResult(BaseModel):
    book_id: int
    title: str
    total_chapters: int
    notice: str | None = None


# --------------------------------------------------------------------------
# 进度 / 对话 / 搜索
# --------------------------------------------------------------------------
class ProgressOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    user_id: int
    book_id: int
    chapter_index: int
    chapter_offset: int
    updated_at: datetime


class ProgressUpdate(BaseModel):
    chapter_index: int | None = Field(default=None, ge=1)
    chapter_offset: int | None = Field(default=None, ge=0)


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=2000)
    quick_read: bool = False


class SearchHit(BaseModel):
    chapter_index: int
    title: str


class SearchResult(BaseModel):
    book_id: int | None
    query: str
    hits: list[SearchHit]