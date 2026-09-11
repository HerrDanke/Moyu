"""简单访问密码 + 签名 Cookie Session。"""
from __future__ import annotations

import hmac

from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

COOKIE_NAME = "moyu_session"
SESSION_MAX_AGE = 60 * 60 * 24 * 30  # 30 天


def verify_password(settings_password: str, candidate: str) -> bool:
    if not settings_password:
        return False
    # 比较 UTF-8 字节：str 直接比较非 ASCII 会抛 TypeError
    return hmac.compare_digest(
        settings_password.encode("utf-8"), candidate.encode("utf-8")
    )


def _serializer(secret_key: str) -> URLSafeTimedSerializer:
    return URLSafeTimedSerializer(secret_key, salt="moyu-session")


def create_session_token(secret_key: str) -> str:
    return _serializer(secret_key).dumps({"ok": True})


def verify_session_token(secret_key: str, token: str | None) -> bool:
    if not token:
        return False
    try:
        _serializer(secret_key).loads(token, max_age=SESSION_MAX_AGE)
        return True
    except (BadSignature, SignatureExpired):
        return False