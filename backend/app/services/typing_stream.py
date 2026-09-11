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


def split_sentences(text: str) -> list[str]:
    parts = [p for p in _SENTENCE_SPLIT.split(text) if p.strip()]
    return parts or ([text] if text else [])


def _sse(payload: dict) -> str:
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"


def _batches(items: list[str], size: int) -> list[str]:
    size = max(1, size)
    return ["".join(items[i : i + size]) for i in range(0, len(items), size)]


async def stream_response(
    response: ChatResponse, settings: Settings
) -> AsyncIterator[str]:
    yield _sse({"type": "start"})

    if response.thinking:
        yield _sse({"type": "thinking", "text": response.thinking})
        await asyncio.sleep(max(0.0, settings.thinking_delay / max(settings.typing_speed, 0.1)))

    if response.title:
        yield _sse({"type": "title", "text": response.title})

    # 快速阅读：一次性给全文（仍按 SSE 事件发送，但无逐句节流）
    if response.kind == "chapter" and settings.typing_speed <= 0:
        yield _sse({"type": "chunk", "text": response.body})
    else:
        for batch in _batches(split_sentences(response.body), settings.chunk_sentences):
            yield _sse({"type": "chunk", "text": batch})
            if response.kind == "chapter":
                lo = settings.stream_min_delay
                hi = max(settings.stream_max_delay, lo)
                delay = random.uniform(lo, hi) / max(settings.typing_speed, 0.1)
                await asyncio.sleep(delay)

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