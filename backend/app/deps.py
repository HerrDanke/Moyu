"""FastAPI 依赖：数据库会话、配置、鉴权守卫。"""
from __future__ import annotations

from collections.abc import Iterator

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from .config import Settings
from .security import COOKIE_NAME, verify_session_token


def get_app_settings(request: Request) -> Settings:
    """从 app.state 取配置（保证与 create_app 注入的实例一致）。"""
    return request.app.state.settings


def get_db(request: Request) -> Iterator[Session]:
    session_factory = request.app.state.session_factory
    session: Session = session_factory()
    try:
        yield session
    finally:
        session.close()


def require_session(
    request: Request,
    settings: Settings = Depends(get_app_settings),
) -> None:
    """未携带有效 Session 时返回 401；未配置密码时直接放行（本地开发）。"""
    if not settings.access_password:
        return
    token = request.cookies.get(COOKIE_NAME)
    if not verify_session_token(settings.secret_key, token):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="未登录")


SessionDep = Depends(get_db)
SettingsDep = Depends(get_app_settings)