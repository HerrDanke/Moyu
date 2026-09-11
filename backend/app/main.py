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
    """未知路径回退到 index.html，支持前端深层路由刷新。

    但 /api/* 的未知路径必须保持 404（不能返回 HTML，否则前端会误判成功）。
    """

    async def get_response(self, path: str, scope):  # type: ignore[override]
        # 注意：path 由 StaticFiles 归一化，Windows 上分隔符是 "\"，且可能带前导斜杠
        normalized = path.replace("\\", "/").lstrip("/")
        if normalized == "api" or normalized.startswith("api/"):
            raise StarletteHTTPException(status_code=404)
        try:
            response = await super().get_response(path, scope)
        except StarletteHTTPException as exc:
            if exc.status_code == 404:
                return await super().get_response("index.html", scope)
            raise
        if response.status_code == 404:
            return await super().get_response("index.html", scope)
        return response


INSECURE_SECRETS = {"", "dev-secret-change-me", "please-change-me", "changeme", "change-me"}


def _assert_secure_config(settings: Settings) -> None:
    """配置了访问密码却使用默认/空密钥时，拒绝启动（否则可伪造 Cookie 绕过鉴权）。"""
    if settings.access_password and settings.secret_key in INSECURE_SECRETS:
        raise RuntimeError(
            "检测到 ACCESS_PASSWORD 已启用但 SECRET_KEY 为默认值/空值。"
            "请设置一个足够随机的 SECRET_KEY（见 .env.example），否则会话可被伪造。"
        )


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    _assert_secure_config(settings)
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