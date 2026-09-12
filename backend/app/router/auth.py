"""账号登录、登出、当前用户、状态、首次引导。

安全要点：
- 引导与登录都先做限速/退避，再做事
- 引导接口**先校验口令、后执行 KDF**，避免被用来放大 CPU
- 「用户不存在」也跑一次等价的 dummy 哈希，抹平响应时间差
"""
from __future__ import annotations

import asyncio

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.responses import JSONResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import INSECURE_SECRETS, Settings
from ..db import backfill_legacy_data, count_users
from ..deps import client_ip, get_app_settings, get_db, resolve_current_user
from ..models import User
from ..schemas import AuthStatus, LoginRequest, SetupRequest, UserOut
from ..security import (
    COOKIE_NAME,
    SESSION_MAX_AGE,
    check_setup_code,
    create_session_token,
    hash_password,
    run_dummy_verify,
    set_setup_code,
    validate_password,
    validate_username,
    verify_password,
)
from ..services import ratelimit

router = APIRouter(prefix="/api/auth", tags=["auth"])

LOGIN_FAILED = "用户名或密码错误"


def _set_session_cookie(response: Response, token: str, secure: bool) -> None:
    response.set_cookie(
        key=COOKIE_NAME,
        value=token,
        max_age=SESSION_MAX_AGE,
        httponly=True,
        samesite="lax",
        secure=secure,
        path="/",
    )


def _issue_session(response: Response, settings: Settings, user: User) -> None:
    token = create_session_token(settings.secret_key, user.id, user.token_version)
    _set_session_cookie(response, token, settings.cookie_secure)


@router.get("/status", response_model=AuthStatus)
def status_(
    request: Request,
    session: Session = Depends(get_db),
    settings: Settings = Depends(get_app_settings),
):
    if count_users(session) == 0:
        # 注意：绝不返回引导口令
        return AuthStatus(setup_required=True, authenticated=False, user=None)
    user = resolve_current_user(request, session, settings)
    return AuthStatus(
        setup_required=False,
        authenticated=user is not None,
        user=UserOut.model_validate(user) if user is not None else None,
    )


@router.post("/setup", response_model=UserOut)
async def setup(
    payload: SetupRequest,
    request: Request,
    response: Response,
    session: Session = Depends(get_db),
    settings: Settings = Depends(get_app_settings),
):
    if count_users(session) > 0:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="系统已存在账号，无需初始化"
        )
    if settings.secret_key in INSECURE_SECRETS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="请先为服务设置随机的 SECRET_KEY（见 .env.example），再完成首次引导",
        )

    if not ratelimit.auth_bucket.allow():
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="尝试过于频繁，请稍后再试"
        )
    throttle_key = f"setup:{client_ip(request)}"
    delay = ratelimit.setup_throttle.delay_for(throttle_key)
    if delay:
        await asyncio.sleep(delay)

    # 先验口令：必须早于任何密码哈希计算
    if not check_setup_code(payload.setup_code):
        ratelimit.setup_throttle.record_failure(throttle_key)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="引导口令不正确"
        )

    try:
        validate_username(payload.username)
        validate_password(payload.password)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    user = User(
        username=payload.username,
        password_hash=hash_password(payload.password),
        is_admin=True,
        is_active=True,
    )
    session.add(user)
    session.commit()
    session.refresh(user)

    ratelimit.setup_throttle.reset(throttle_key)
    set_setup_code(None)  # 引导入口永久关闭

    # 把老数据归给首个管理员
    backfill_legacy_data(request.app.state.engine, user.id)

    _issue_session(response, settings, user)
    return UserOut.model_validate(user)


@router.post("/login", response_model=UserOut)
async def login(
    payload: LoginRequest,
    request: Request,
    response: Response,
    session: Session = Depends(get_db),
    settings: Settings = Depends(get_app_settings),
):
    if not ratelimit.auth_bucket.allow():
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="尝试过于频繁，请稍后再试"
        )
    throttle_key = f"{client_ip(request)}:{payload.username}"
    delay = ratelimit.login_throttle.delay_for(throttle_key)
    if delay:
        await asyncio.sleep(delay)

    user = session.scalar(select(User).where(User.username == payload.username))
    if user is None:
        run_dummy_verify()
        ratelimit.login_throttle.record_failure(throttle_key)
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED, content={"detail": LOGIN_FAILED}
        )

    if not verify_password(user.password_hash, payload.password) or not user.is_active:
        ratelimit.login_throttle.record_failure(throttle_key)
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED, content={"detail": LOGIN_FAILED}
        )

    ratelimit.login_throttle.reset(throttle_key)
    _issue_session(response, settings, user)
    return UserOut.model_validate(user)


@router.post("/logout")
def logout(response: Response):
    response.delete_cookie(COOKIE_NAME, path="/")
    return {"ok": True}


@router.get("/me", response_model=UserOut)
def me(
    request: Request,
    session: Session = Depends(get_db),
    settings: Settings = Depends(get_app_settings),
):
    user = resolve_current_user(request, session, settings)
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="未登录")
    return UserOut.model_validate(user)