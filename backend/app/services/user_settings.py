"""每用户设置的键定义与「思考强度」档位。

档位是**唯一事实源**：前端不硬编码这套映射，而是从 `GET /api/settings` 读回来。
`typing_speed` 是「延迟除数」（间隔 = 基准 / typing_speed），所以值越大越快。
"""
from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.orm import Session

from ..config import Settings
from ..models import User
from . import store

TYPING_SPEED_KEY = "typing_speed"

MIN_TYPING_SPEED = 0.1
MAX_TYPING_SPEED = 10.0


@dataclass(frozen=True)
class ThinkingLevel:
    level: int
    name: str
    speed: float
    hint: str


# 档位越高 = 思考越"深" = 出字越慢。叙事上贴合「伪装成大模型」。
THINKING_LEVELS: tuple[ThinkingLevel, ...] = (
    ThinkingLevel(1, "迅捷", 2.0, "几乎不停顿，一口气往外走"),
    ThinkingLevel(2, "标准", 1.0, "默认节奏"),
    ThinkingLevel(3, "深入", 0.6, "一句一句慢慢斟酌"),
    ThinkingLevel(4, "沉思", 0.35, "明显停顿，像是在深思"),
)

DEFAULT_LEVEL = 2


def levels_payload() -> list[dict]:
    return [
        {"level": lv.level, "name": lv.name, "speed": lv.speed, "hint": lv.hint}
        for lv in THINKING_LEVELS
    ]


def speed_for_level(level: int) -> float:
    for lv in THINKING_LEVELS:
        if lv.level == level:
            return lv.speed
    raise ValueError("档位超出范围")


def level_for_speed(speed: float | None) -> int | None:
    """把速度值映射回档位；不是任何档位对应的值时返回 None。"""
    if speed is None:
        return None
    for lv in THINKING_LEVELS:
        if abs(lv.speed - speed) < 1e-6:
            return lv.level
    return None


def validate_typing_speed(value: float) -> float:
    """范围校验：挡住 0 / 负数 / 极大值，避免服务端 sleep 出怪行为。"""
    if value < MIN_TYPING_SPEED or value > MAX_TYPING_SPEED:
        raise ValueError(f"速度需在 {MIN_TYPING_SPEED}~{MAX_TYPING_SPEED} 之间")
    return value


def effective_typing_speed(
    session: Session, settings: Settings, user: User
) -> tuple[float, bool]:
    """返回 (速度, 是否来自用户设置)。未设置过时回落到环境变量带来的默认值。"""
    raw = store.get_user_setting(session, user.id, TYPING_SPEED_KEY)
    if raw is not None:
        try:
            return float(raw), True
        except ValueError:
            pass
    return settings.typing_speed, False


def with_user_pacing(settings: Settings, session: Session, user: User) -> Settings:
    """把当前用户的思考强度套用到本次请求的实际配置上。"""
    from dataclasses import replace

    speed, _ = effective_typing_speed(session, settings, user)
    if speed == settings.typing_speed:
        return settings
    return replace(settings, typing_speed=speed)