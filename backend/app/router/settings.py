"""每用户设置：读取与更新（当前包含「思考强度」对应的生成速度）。"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ..deps import get_app_settings, get_db, require_session
from ..config import Settings
from ..models import User
from ..services import store
from ..services.user_settings import (
    TYPING_SPEED_KEY,
    effective_typing_speed,
    level_for_speed,
    levels_payload,
    validate_typing_speed,
)

router = APIRouter(prefix="/api/settings", tags=["settings"])


class SettingsOut(BaseModel):
    typing_speed: float
    thinking_level: int | None
    levels: list[dict]
    typing_speed_from_user: bool


class SettingsUpdate(BaseModel):
    typing_speed: float | None = Field(default=None)


@router.get("", response_model=SettingsOut)
def get_settings(
    session: Session = Depends(get_db),
    settings: Settings = Depends(get_app_settings),
    user: User = Depends(require_session),
):
    speed, from_user = effective_typing_speed(session, settings, user)
    return SettingsOut(
        typing_speed=speed,
        thinking_level=level_for_speed(speed),
        levels=levels_payload(),
        typing_speed_from_user=from_user,
    )


@router.patch("", response_model=SettingsOut)
def update_settings(
    payload: SettingsUpdate,
    session: Session = Depends(get_db),
    settings: Settings = Depends(get_app_settings),
    user: User = Depends(require_session),
):
    if payload.typing_speed is not None:
        try:
            value = validate_typing_speed(float(payload.typing_speed))
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
            ) from exc
        store.set_user_setting(session, user.id, TYPING_SPEED_KEY, repr(value))

    speed, from_user = effective_typing_speed(session, settings, user)
    return SettingsOut(
        typing_speed=speed,
        thinking_level=level_for_speed(speed),
        levels=levels_payload(),
        typing_speed_from_user=from_user,
    )