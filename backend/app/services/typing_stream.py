"""把 ChatResponse 变成带节奏的 SSE 字节流。

关键：所有正文在进入本模块前已从 DB 取出（零 DB 访问），
这里只做内存分批 + asyncio.sleep 节流。
"""
from __future__ import annotations

import asyncio
import json
import random
import re
from collections.abc import AsyncIterator

from ..config import Settings
from .chat_engine import ChatResponse

_SENTENCE_SPLIT = re.compile(r"(?<=[。！？!?…；;\n])")
QUICK_READ_HEAD_BATCHES = 3


def split_sentences(text: str) -> list[str]:
    """按句切分，且保证 `"".join(结果) == text`。

    注意：不能用 `p.strip()` 过滤——`re.split` 会把「只含换行」的片段单独切出来，
    strip 后判空即被丢弃，导致章节的段落分隔在流式阶段就被抹掉（长章节会糊成一坨）。
    这里只丢掉真正的空串。
    """
    parts = [p for p in _SENTENCE_SPLIT.split(text) if p != ""]
    return parts or ([text] if text else [])


def _sse(payload: dict) -> str:
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"


def _batches(items: list[str], size: int) -> list[str]:
    size = max(1, size)
    return ["".join(items[i : i + size]) for i in range(0, len(items), size)]


async def _paced_delay(settings: Settings) -> None:
    # typing_speed <= 0 表示不节流（测试 / 快速模式）
    if settings.typing_speed <= 0:
        return
    lo = settings.stream_min_delay
    hi = max(settings.stream_max_delay, lo)
    await asyncio.sleep(random.uniform(lo, hi) / settings.typing_speed)


async def stream_response(
    response: ChatResponse, settings: Settings, quick_read: bool = False
) -> AsyncIterator[str]:
    yield _sse({"type": "start"})

    if response.progress_book_id is not None:
        # 让前端把「当前书」同步为服务端认定的书
        yield _sse({"type": "book", "id": response.progress_book_id})

    if response.kind == "chapter" and response.meta_chapter_index is not None:
        yield _sse(
            {
                "type": "meta",
                "chapter_index": response.meta_chapter_index,
                "start_offset": response.meta_start_offset,
                "char_count": response.meta_char_count,
            }
        )

    if response.thinking:
        yield _sse({"type": "thinking", "text": response.thinking})
        if settings.typing_speed > 0:
            await asyncio.sleep(settings.thinking_delay / settings.typing_speed)

    if response.title:
        yield _sse({"type": "title", "text": response.title})

    batches = _batches(split_sentences(response.body), settings.chunk_sentences)

    if quick_read:
        # 快速阅读：只演开头三段，其余一次性送达
        for batch in batches[:QUICK_READ_HEAD_BATCHES]:
            yield _sse({"type": "chunk", "text": batch})
            if response.kind == "chapter":
                await _paced_delay(settings)
        rest = "".join(batches[QUICK_READ_HEAD_BATCHES:])
        if rest:
            yield _sse({"type": "chunk", "text": rest})
    else:
        for batch in batches:
            yield _sse({"type": "chunk", "text": batch})
            if response.kind == "chapter":
                await _paced_delay(settings)

    if response.footer:
        yield _sse({"type": "footer", "text": response.footer})

    yield _sse({"type": "done"})
    yield "data: [DONE]\n\n"


def stream_headers() -> dict[str, str]:
    return {
        "Content-Type": "text/event-stream; charset=utf-8",
        "Cache-Control": "no-cache",
        "X-Accel-Buffering": "no",
    }