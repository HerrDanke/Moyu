from __future__ import annotations

from app.readers.txt_reader import TxtReader, decode_bytes

from .conftest import SAMPLE_TXT


def test_split_by_headings():
    reader = TxtReader()
    result = reader.read(SAMPLE_TXT.encode("utf-8"))
    assert result.used_fallback is False
    assert result.total_chapters == 3
    assert result.chapters[0].index_no == 1
    assert "第一章" in result.chapters[0].title
    assert "青石阶" in result.chapters[0].content
    assert result.chapters[2].index_no == 3


def test_fallback_split_without_headings():
    text = "这是一段没有任何章节标题的长文本。" * 200
    reader = TxtReader(fallback_chapter_chars=300)
    result = reader.read(text.encode("utf-8"))
    assert result.used_fallback is True
    assert result.total_chapters > 1
    assert result.chapters[0].title == "第 1 章"
    assert all(len(c.content) <= 300 for c in result.chapters)


def test_gbk_decoding():
    data = SAMPLE_TXT.encode("gb18030")
    text, enc = decode_bytes(data)
    assert "青石阶" in text
    reader = TxtReader()
    result = reader.read(data)
    assert result.total_chapters == 3
    assert "灵气" in result.chapters[1].content
    assert "灵光" in result.chapters[1].title


def test_oversized_chapter_split():
    long_body = "字" * 2500
    text = f"第一章 长\n{long_body}\n"
    reader = TxtReader(max_chapter_chars=1000)
    result = reader.read(text.encode("utf-8"))
    assert result.total_chapters == 3
    assert result.chapters[0].title == "第一章 长"
    assert result.chapters[1].title.endswith("（2）")


def test_empty_input():
    reader = TxtReader()
    result = reader.read(b"")
    assert result.total_chapters == 0