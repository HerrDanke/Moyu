"""FastAPI 应用入口：注册 API 路由，最后挂载前端静态产物（含 SPA fallback）。"""
from __future__ import annotations

import logging
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException

from .config import INSECURE_SECRETS, Settings, get_settings
from .db import count_users, create_engine_for, create_session_factory, init_db
from .router import auth, books, chat, progress, search, settings as settings_router, users
from .security import generate_setup_code, set_setup_code

logger = logging.getLogger("moyu")

INSECURE_SECRET_HINT = (
    "SECRET_KEY 为空或属于默认弱值。请设置一个足够随机的值（例如 `openssl rand -hex 32`），"
    "见 .env.example。否则任何人都能用这个公开常量自签会话 Cookie，绕过鉴权。"
)


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


def assert_secure_secret(settings: Settings) -> None:
    """已存在用户时，弱密钥必须拒绝启动。

    注意：这里**不能**再依赖 ACCESS_PASSWORD —— 账号体系下该变量已退役，
    沿用旧条件会恒为假，从而允许用公开的默认常量签发可伪造的会话 Cookie。
    """
    if settings.secret_key in INSECURE_SECRETS:
        raise RuntimeError(INSECURE_SECRET_HINT)


def setup_required(session_factory) -> bool:
    session = session_factory()
    try:
        return count_users(session) == 0
    finally:
        session.close()


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    settings.ensure_dirs()

    app = FastAPI(title="Moyu", version="0.2.0")
    engine = create_engine_for(settings)
    init_db(engine)
    session_factory = create_session_factory(engine)
    app.state.engine = engine
    app.state.session_factory = session_factory
    app.state.settings = settings

    # 有用户却用弱密钥 → 拒绝启动
    if not setup_required(session_factory):
        assert_secure_secret(settings)
    else:
        # 首次运行：生成一次性引导口令（只出现在服务器日志里）
        code = generate_setup_code()
        set_setup_code(code)
        logger.warning(
            "[setup] 尚未创建任何账号。请打开应用并按提示创建管理员，引导口令：%s "
            "（该口令仅在本次启动期间有效）",
            code,
        )
        print(
            f"\n[setup] 未检测到任何用户。首次引导口令：{code}\n"
            f"[setup] 若 SECRET_KEY 仍为默认值，请在完成引导前先设置一个随机值。\n",
            flush=True,
        )
        if settings.secret_key in INSECURE_SECRETS:
            logger.warning("[setup] 当前 SECRET_KEY 为默认弱值，引导接口会拒绝创建管理员。")

    # 1) 先注册所有 /api/* 路由
    app.include_router(auth.router)
    app.include_router(users.router)
    app.include_router(settings_router.router)
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