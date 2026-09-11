"""Reader 抽象接口：为未来 EPUB 等格式预留扩展位。"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class ParsedChapter:
    index_no: int
    title: str
    content: str

    @property
    def char_count(self) -> int:
        return len(self.content)


@dataclass
class ParseResult:
    chapters: list[ParsedChapter] = field(default_factory=list)
    used_fallback: bool = False
    encoding: str = "utf-8"

    @property
    def total_chapters(self) -> int:
        return len(self.chapters)


class BaseReader(ABC):
    """把原始字节解析为章节列表。"""

    @abstractmethod
    def read(self, data: bytes) -> ParseResult:  # pragma: no cover - interface
        raise NotImplementedError