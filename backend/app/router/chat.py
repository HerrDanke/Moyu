"""对话流：POST /api/chat → text/event-stream。

进度写入放在流式结束之后（客户端中途断开则不推进）。
"""
from __future__ import annotations

from dataclasses import replace

from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from ..config import Settings
from ..deps import get_app_settings, get_db, require_session
from ..schemas import ChatRequest
from ..services import store
from ..services.chat_engine import build_response
from ..services.typing_stream import stream_headers, stream_response

router = APIRouter(
    prefix="/api/chat", tags=["chat"], dependencies=[Depends(require_session)]
)


@router.post("")
async def chat(
    request: Request,
    payload: ChatRequest,
    session: Session = Depends(get_db),
    settings: Settings = Depends(get_app_settings),
):
    response = build_response(session, settings, payload.message)
    # 快速阅读：不做逐句节流，正文尽快分批送达
    eff_settings = replace(settings, typing_speed=1000.0) if payload.quick_read else settings
    progress = (
        response.progress_book_id,
        response.progress_chapter_index,
        response.progress_offset or 0,
    )
    session_factory = request.app.state.session_factory

    async def event_generator():
        async for chunk in stream_response(response, eff_settings):
            yield chunk
        # 流式正常结束后才推进进度
        if progress[0] is not None:
            fresh = session_factory()
            try:
                store.write_progress(fresh, progress[0], progress[1] or 1, progress[2])
            finally:
                fresh.close()

    return StreamingResponse(
        event_generator(), media_type="text/event-stream", headers=stream_headers()
    )