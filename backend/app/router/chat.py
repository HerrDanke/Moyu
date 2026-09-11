"""对话流：POST /api/chat → text/event-stream。

进度写入放在流式结束之后（客户端中途断开则不推进）。
"""
from __future__ import annotations

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
    book_id = response.progress_book_id
    chapter_index = response.progress_chapter_index
    offset = response.progress_offset or 0
    conditional_from = (
        response.progress_prev_index if response.progress_conditional else None
    )
    session_factory = request.app.state.session_factory

    async def event_generator():
        async for chunk in stream_response(response, settings, quick_read=payload.quick_read):
            yield chunk
        # 流式正常结束后才推进进度（条件更新防多标签页重复推进）
        if book_id is not None:
            fresh = session_factory()
            try:
                store.write_progress(
                    fresh,
                    book_id,
                    chapter_index or 1,
                    offset,
                    conditional_from=conditional_from,
                )
            finally:
                fresh.close()

    return StreamingResponse(
        event_generator(), media_type="text/event-stream", headers=stream_headers()
    )