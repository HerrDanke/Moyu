"""管理员用户管理：列表 / 创建 / 更新 / 删除。

保护规则（安全评审补强）：
- 不能删除或停用自己
- 不能删除、降级或停用**最后一个仍在启用的管理员**
- 改密 / 停用 / 删除都会自增 token_version，立即吊销对方会话
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..deps import get_db, require_admin
from ..models import User
from ..schemas import UserCreate, UserOut, UserUpdate
from ..security import hash_password, validate_password, validate_username

router = APIRouter(prefix="/api/users", tags=["users"])


def _active_admin_count(session: Session) -> int:
    return (
        session.scalar(
            select(func.count(User.id)).where(User.is_admin.is_(True), User.is_active.is_(True))
        )
        or 0
    )


def _get_or_404(session: Session, user_id: int) -> User:
    user = session.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="用户不存在")
    return user


@router.get("", response_model=list[UserOut])
def list_users(
    session: Session = Depends(get_db), _admin: User = Depends(require_admin)
):
    users = session.scalars(select(User).order_by(User.id.asc())).all()
    return [UserOut.model_validate(u) for u in users]


@router.post("", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def create_user(
    payload: UserCreate,
    session: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
):
    try:
        validate_username(payload.username)
        validate_password(payload.password)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    exists = session.scalar(select(User).where(User.username == payload.username))
    if exists is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="用户名已被占用")

    user = User(
        username=payload.username,
        password_hash=hash_password(payload.password),
        is_admin=payload.is_admin,
        is_active=True,
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    return UserOut.model_validate(user)


@router.patch("/{user_id}", response_model=UserOut)
def update_user(
    user_id: int,
    payload: UserUpdate,
    session: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    user = _get_or_404(session, user_id)

    wants_demote = payload.is_admin is False and user.is_admin
    wants_disable = payload.is_active is False and user.is_active

    if user.id == admin.id and (wants_demote or wants_disable):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="不能停用或降级自己的账号"
        )
    if (wants_demote or wants_disable) and user.is_admin and _active_admin_count(session) <= 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="不能移除最后一个可用的管理员",
        )

    if payload.password is not None:
        try:
            validate_password(payload.password)
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
        user.password_hash = hash_password(payload.password)
        user.token_version += 1  # 改密即吊销既有会话

    if payload.is_admin is not None:
        user.is_admin = payload.is_admin
    if payload.is_active is not None:
        user.is_active = payload.is_active
        if payload.is_active is False:
            user.token_version += 1  # 停用即吊销既有会话

    session.commit()
    session.refresh(user)
    return UserOut.model_validate(user)


@router.delete("/{user_id}")
def delete_user(
    user_id: int,
    session: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    user = _get_or_404(session, user_id)
    if user.id == admin.id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="不能删除自己的账号")
    if user.is_admin and _active_admin_count(session) <= 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="不能移除最后一个可用的管理员"
        )

    session.delete(user)  # 其 progress 由外键级联删除
    session.commit()
    return {"ok": True}