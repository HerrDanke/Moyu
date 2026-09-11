"""TXT 小说解析器。

- 编码自动探测（UTF-8 / GBK / GB18030）
- 章节标题识别（正则，保持线性、无嵌套量词，避免 ReDoS）
- 无分隔时按字数兜底切分
- 单章超上限时再拆，避免流式过久
"""
from __future__ import annotations

import re

from charset_normalizer import from_bytes

from .base import BaseReader, ParsedChapter, ParseResult

# 线性正则：第 X 章/回/节/卷/话（数字支持阿拉伯与中文），标题限制长度
CHAPTER_RE = re.compile(
    r"^第\s*[0-9０-９零一二三四五六七八九十百千万两]+\s*[章回节卷话][^\n]{0,40}$"
)
_MAX_TITLE_LEN = 60


def decode_bytes(data: bytes) -> tuple[str, str]:
    """返回 (文本, 编码名)。

    顺序：BOM → UTF-8（严格）→ GB18030（严格）→ charset-normalizer 兜底。
    中文小说绝大多数为 UTF-8 或 GBK/GB18030，严格解码更可预测。
    """
    if not data:
        return "", "utf-8"
    for bom, enc in ((b"\xef\xbb\xbf", "utf-8-sig"), (b"\xff\xfe", "utf-16-le"), (b"\xfe\xff", "utf-16-be")):
        if data.startswith(bom):
            try:
                return data.decode(enc), enc
            except UnicodeDecodeError:
                break
    for enc in ("utf-8", "gb18030"):
        try:
            return data.decode(enc), enc
        except UnicodeDecodeError:
            continue
    best = from_bytes(data).best()
    if best is not None:
        try:
            return str(best), best.encoding or "utf-8"
        except Exception:  # noqa: BLE001 - 探测结果不可用时回退
            pass
    raise ValueError("无法解码文件：不支持的编码")


class TxtReader(BaseReader):
    def __init__(
        self,
        *,
        max_chapter_chars: int = 100_000,
        fallback_chapter_chars: int = 3000,
    ) -> None:
        self.max_chapter_chars = max(1, max_chapter_chars)
        self.fallback_chapter_chars = max(1, fallback_chapter_chars)

    def read(self, data: bytes) -> ParseResult:
        text, encoding = decode_bytes(data)
        text = text.replace("\r\n", "\n").replace("\r", "\n")
        headings = self._find_headings(text)

        if not headings:
            chapters = self._fallback_split(text)
            return ParseResult(chapters=chapters, used_fallback=True, encoding=encoding)

        chapters = self._split_by_headings(text, headings)
        chapters = self._split_oversized(chapters)
        return ParseResult(chapters=chapters, used_fallback=False, encoding=encoding)

    @staticmethod
    def _find_headings(text: str) -> list[tuple[int, str]]:
        """返回 [(行起始偏移, 标题)]，仅收录命中标题特征的短行。"""
        headings: list[tuple[int, str]] = []
        offset = 0
        for line in text.split("\n"):
            stripped = line.strip()
            if stripped and len(stripped) <= _MAX_TITLE_LEN and CHAPTER_RE.match(stripped):
                headings.append((offset, stripped))
            offset += len(line) + 1  # +1 为换行符
        return headings

    @staticmethod
    def _split_by_headings(text: str, headings: list[tuple[int, str]]) -> list[ParsedChapter]:
        chapters: list[ParsedChapter] = []
        for i, (start, title) in enumerate(headings):
            end = headings[i + 1][0] if i + 1 < len(headings) else len(text)
            body = text[start:end]
            # 去掉标题行本身
            body = body.split("\n", 1)[1] if "\n" in body else ""
            content = body.strip()
            chapters.append(ParsedChapter(index_no=i + 1, title=title.strip(), content=content))
        return chapters

    def _fallback_split(self, text: str) -> list[ParsedChapter]:
        cleaned = text.strip()
        if not cleaned:
            return []
        size = self.fallback_chapter_chars
        chapters: list[ParsedChapter] = []
        for i in range(0, len(cleaned), size):
            index_no = len(chapters) + 1
            chapters.append(
                ParsedChapter(index_no=index_no, title=f"第 {index_no} 章", content=cleaned[i : i + size])
            )
        return chapters

    def _split_oversized(self, chapters: list[ParsedChapter]) -> list[ParsedChapter]:
        result: list[ParsedChapter] = []
        for chapter in chapters:
            content = chapter.content
            if len(content) <= self.max_chapter_chars:
                result.append(
                    ParsedChapter(
                        index_no=len(result) + 1, title=chapter.title, content=content
                    )
                )
                continue
            parts = [
                content[i : i + self.max_chapter_chars]
                for i in range(0, len(content), self.max_chapter_chars)
            ]
            for k, part in enumerate(parts):
                title = chapter.title if k == 0 else f"{chapter.title}（{k + 1}）"
                result.append(
                    ParsedChapter(index_no=len(result) + 1, title=title, content=part)
                )
        return result