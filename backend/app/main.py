"""FastAPI 应用入口：注册 API 路由，最后挂载前端静态产物（含 SPA fallback）。"""
from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException

from .config import Settings, get_settings
from .db import create_engine_for, create_session_factory, init_db
from .router import auth, books, chat, progress, search


class SPAStaticFiles(StaticFiles):
    """未知路径回退到 index.html，支持前端深层路由刷新。"""

    async def get_response(self, path: str, scope):  # type: ignore[override]
        try:
            response = await super().get_response(path, scope)
        except StarletteHTTPException as exc:
            if exc.status_code == 404:
                return await super().get_response("index.html", scope)
            raise
        if response.status_code == 404:
            return await super().get_response("index.html", scope)
        return response


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    settings.ensure_dirs()

    app = FastAPI(title="Moyu", version="0.1.0")
    engine = create_engine_for(settings)
    init_db(engine)
    app.state.engine = engine
    app.state.session_factory = create_session_factory(engine)
    app.state.settings = settings

    # 1) 先注册所有 /api/* 路由
    app.include_router(auth.router)
    app.include_router(books.router)
    app.include_router(progress.router)
    app.include_router(search.router)
    app.include_router(chat.router)

    @app.get("/api/health")
    def health():
        return {"ok": True}

    # 2) 最后挂载静态资源（必须晚于 /api，否则会吞掉 API 路由）
    static_dir = Path(settings.static_dir)
    if static_dir.is_dir():
        app.mount("/", SPAStaticFiles(directory=static_dir, html=True), name="static")

    return app


app = create_app()