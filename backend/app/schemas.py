"""Pydantic 请求/响应模型。"""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class BookOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    source_filename: str
    total_chapters: int
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


class ProgressOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    book_id: int
    chapter_index: int
    chapter_offset: int
    updated_at: datetime


class ProgressUpdate(BaseModel):
    chapter_index: int | None = Field(default=None, ge=1)
    chapter_offset: int | None = Field(default=None, ge=0)


class LoginRequest(BaseModel):
    password: str = Field(min_length=1, max_length=512)


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