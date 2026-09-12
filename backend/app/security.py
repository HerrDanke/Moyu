"""账号安全：密码哈希、可吊销会话、首次引导口令。

设计取舍：
- 只用标准库（scrypt，不支持时回退 pbkdf2），不引入第三方密码库
- KDF 外包一层全局信号量：scrypt 每次约 16MiB，弱机器上并发登录会打爆内存
- 会话载荷带 token_version：改密/停用后旧 Cookie 立即失效
"""
from __future__ import annotations

import hashlib
import hmac
import os
import re
import secrets
import threading

from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

COOKIE_NAME = "moyu_session"
SESSION_MAX_AGE = 60 * 60 * 24 * 30  # 30 天

PASSWORD_MIN_LENGTH = 4
PASSWORD_MAX_LENGTH = 512
USERNAME_MIN_LENGTH = 3
USERNAME_MAX_LENGTH = 32

SCRYPT_N = 2**14
SCRYPT_R = 8
SCRYPT_P = 1
PBKDF2_ITERATIONS = 600_000

# 同时最多 2 个 KDF 在跑，超出排队
_KDF_SEMAPHORE = threading.BoundedSemaphore(2)
_USERNAME_RE = re.compile(r"[A-Za-z0-9_-]+")


# --------------------------------------------------------------------------
# 密码哈希
# --------------------------------------------------------------------------
def hash_password(password: str) -> str:
    salt = os.urandom(16)
    raw = password.encode("utf-8")
    try:
        with _KDF_SEMAPHORE:
            dk = hashlib.scrypt(
                raw, salt=salt, n=SCRYPT_N, r=SCRYPT_R, p=SCRYPT_P, dklen=32
            )
        return f"scrypt${salt.hex()}${dk.hex()}"
    except (ValueError, AttributeError, TypeError):
        with _KDF_SEMAPHORE:
            dk = hashlib.pbkdf2_hmac("sha256", raw, salt, PBKDF2_ITERATIONS, dklen=32)
        return f"pbkdf2${salt.hex()}${dk.hex()}"


def verify_password(stored: str, candidate: str) -> bool:
    try:
        algo, salt_hex, dk_hex = stored.split("$")
        salt = bytes.fromhex(salt_hex)
        expected = bytes.fromhex(dk_hex)
    except (ValueError, AttributeError):
        return False

    raw = candidate.encode("utf-8")
    try:
        with _KDF_SEMAPHORE:
            if algo == "scrypt":
                actual = hashlib.scrypt(
                    raw, salt=salt, n=SCRYPT_N, r=SCRYPT_R, p=SCRYPT_P, dklen=len(expected)
                )
            elif algo == "pbkdf2":
                actual = hashlib.pbkdf2_hmac(
                    "sha256", raw, salt, PBKDF2_ITERATIONS, dklen=len(expected)
                )
            else:
                return False
    except (ValueError, AttributeError, TypeError):
        return False
    return hmac.compare_digest(expected, actual)


_dummy_lock = threading.Lock()
_dummy_hash: str | None = None


def run_dummy_verify() -> None:
    """用户不存在时也跑一次等价的 KDF，抹平响应时间差（防用户名枚举）。"""
    global _dummy_hash
    if _dummy_hash is None:
        with _dummy_lock:
            if _dummy_hash is None:
                _dummy_hash = hash_password("moyu-timing-equalizer")
    verify_password(_dummy_hash, "definitely-not-the-password")


def validate_username(username: str) -> str:
    if not (USERNAME_MIN_LENGTH <= len(username) <= USERNAME_MAX_LENGTH):
        raise ValueError(f"用户名长度需在 {USERNAME_MIN_LENGTH}–{USERNAME_MAX_LENGTH} 之间")
    if not _USERNAME_RE.fullmatch(username):
        raise ValueError("用户名只能包含字母、数字、下划线与连字符")
    return username


def validate_password(password: str) -> str:
    if len(password) < PASSWORD_MIN_LENGTH:
        raise ValueError(f"密码至少 {PASSWORD_MIN_LENGTH} 位")
    if len(password) > PASSWORD_MAX_LENGTH:
        raise ValueError(f"密码最多 {PASSWORD_MAX_LENGTH} 位")
    return password


# --------------------------------------------------------------------------
# 会话
# --------------------------------------------------------------------------
def _serializer(secret_key: str) -> URLSafeTimedSerializer:
    return URLSafeTimedSerializer(secret_key, salt="moyu-session-v2")


def create_session_token(secret_key: str, user_id: int, token_version: int) -> str:
    return _serializer(secret_key).dumps({"uid": user_id, "tv": token_version})


def read_session_token(secret_key: str, token: str | None) -> tuple[int, int] | None:
    """返回 (user_id, token_version)；无效或旧格式一律 None。"""
    if not token:
        return None
    try:
        data = _serializer(secret_key).loads(token, max_age=SESSION_MAX_AGE)
    except (BadSignature, SignatureExpired):
        return None
    if not isinstance(data, dict):
        return None
    uid, tv = data.get("uid"), data.get("tv")
    if not isinstance(uid, int) or not isinstance(tv, int):
        return None
    return uid, tv


# --------------------------------------------------------------------------
# 首次引导口令（只在服务器日志里出现）
# --------------------------------------------------------------------------
_SETUP_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
_setup_code: str | None = None
_setup_lock = threading.Lock()


def generate_setup_code() -> str:
    """4 段 5 字符，约 100 bit 熵。"""
    parts = ["".join(secrets.choice(_SETUP_ALPHABET) for _ in range(5)) for _ in range(4)]
    return "-".join(parts)


def set_setup_code(code: str | None) -> None:
    global _setup_code
    with _setup_lock:
        _setup_code = code


def check_setup_code(candidate: str) -> bool:
    with _setup_lock:
        code = _setup_code
    if not code:
        return False
    return hmac.compare_digest(code, candidate or "")