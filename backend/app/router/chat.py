"""对话流：POST /api/chat → text/event-stream。

进度写入放在流式结束之后（客户端中途断开则不推进），且按当前登录用户记账。
"""
from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from ..config import Settings
from ..deps import get_app_settings, get_db, require_session
from ..models import User
from ..schemas import ChatRequest
from ..services import store
from ..services.chat_engine import build_response
from ..services.typing_stream import stream_headers, stream_response
from ..services.user_settings import with_user_pacing

router = APIRouter(prefix="/api/chat", tags=["chat"])

logger = logging.getLogger("moyu.chat")


@router.post("")
async def chat(
    request: Request,
    payload: ChatRequest,
    session: Session = Depends(get_db),
    settings: Settings = Depends(get_app_settings),
    user: User = Depends(require_session),
):
    response = build_response(session, settings, payload.message, user)
    # 用当前用户的「思考强度」覆盖本次请求的节奏（未设置过则回落到环境变量默认值）
    effective = with_user_pacing(settings, session, user)
    user_id = user.id
    book_id = response.progress_book_id
    chapter_index = response.progress_chapter_index
    offset = response.progress_offset or 0
    conditional_from = (
        response.progress_prev_index if response.progress_conditional else None
    )
    session_factory = request.app.state.session_factory

    async def event_generator():
        async for chunk in stream_response(response, effective, quick_read=payload.quick_read):
            yield chunk
        # 流式正常结束后才推进进度。
        # 注意：这里不能静默吞异常——进度写失败会导致「界面在第 9 章、进度还在第 2 章」，
        # 下一次「下一章」就会跳错章。至少要留下日志。
        # 例外：「继续本章」不改章号，偏移由前端实时上报，服务端**不写**——
        # 否则会把请求时刻读到的旧偏移写回去，回滚用户真正读到的位置。
        if book_id is not None and not response.progress_skip_write:
            fresh = session_factory()
            try:
                store.write_progress(
                    fresh,
                    user_id,
                    book_id,
                    chapter_index or 1,
                    offset,
                    conditional_from=conditional_from,
                )
            except Exception:  # noqa: BLE001
                fresh.rollback()
                logger.exception(
                    "写入阅读进度失败：user=%s book=%s chapter=%s",
                    user_id,
                    book_id,
                    chapter_index,
                )
            finally:
                fresh.close()

    return StreamingResponse(
        event_generator(), media_type="text/event-stream", headers=stream_headers()
    )