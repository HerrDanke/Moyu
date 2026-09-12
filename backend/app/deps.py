"""FastAPI 依赖：数据库会话、配置、鉴权守卫。

守卫语义（安全评审补强）：
- 无有效会话 → 401
- 库中没有任何用户（尚未完成首次引导）→ 同样 401，
  避免在「创建首个管理员」之前被任何人读走书库与遗留进度
- 会话每次请求都查库，校验 用户存在 + 启用 + token_version 一致，
  因此改密/停用/删除后旧 Cookie 立即失效
"""
from __future__ import annotations

from collections.abc import Iterator

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from .config import Settings
from .models import User
from .security import COOKIE_NAME, read_session_token


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


def resolve_current_user(
    request: Request, session: Session, settings: Settings
) -> User | None:
    data = read_session_token(settings.secret_key, request.cookies.get(COOKIE_NAME))
    if data is None:
        return None
    user_id, token_version = data
    user = session.get(User, user_id)
    if user is None or not user.is_active or user.token_version != token_version:
        return None
    return user


def require_session(
    request: Request,
    session: Session = Depends(get_db),
    settings: Settings = Depends(get_app_settings),
) -> User:
    """返回当前登录用户；未登录返回 401。"""
    user = resolve_current_user(request, session, settings)
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="未登录")
    return user


# 语义别名：注入当前用户
get_current_user = require_session


def require_admin(user: User = Depends(require_session)) -> User:
    if not user.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="需要管理员权限")
    return user


def client_ip(request: Request) -> str:
    """限速用的来源标识。反代场景优先取 X-Forwarded-For 的首段。"""
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


SessionDep = Depends(get_db)
SettingsDep = Depends(get_app_settings)