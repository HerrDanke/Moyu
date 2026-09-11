"""登录 / 登出 / 状态。"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Request, Response, status
from fastapi.responses import JSONResponse

from ..config import Settings
from ..deps import get_app_settings
from ..schemas import LoginRequest
from ..security import (
    COOKIE_NAME,
    SESSION_MAX_AGE,
    create_session_token,
    verify_password,
    verify_session_token,
)

router = APIRouter(prefix="/api/auth", tags=["auth"])


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


@router.post("/login")
def login(
    payload: LoginRequest,
    response: Response,
    settings: Settings = Depends(get_app_settings),
):
    if settings.access_password and not verify_password(
        settings.access_password, payload.password
    ):
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED, content={"detail": "密码错误"}
        )
    _set_session_cookie(response, create_session_token(settings.secret_key), settings.cookie_secure)
    return {"ok": True}


@router.post("/logout")
def logout(response: Response):
    response.delete_cookie(COOKIE_NAME, path="/")
    return {"ok": True}


@router.get("/status")
def status_(request: Request, settings: Settings = Depends(get_app_settings)):
    if not settings.access_password:
        return {"password_required": False, "authenticated": True}
    token = request.cookies.get(COOKIE_NAME)
    return {
        "password_required": True,
        "authenticated": verify_session_token(settings.secret_key, token),
    }