"""小说解析器。"""
from .base import BaseReader, ParsedChapter, ParseResult
from .txt_reader import TxtReader, decode_bytes

__all__ = ["BaseReader", "ParsedChapter", "ParseResult", "TxtReader", "decode_bytes"]