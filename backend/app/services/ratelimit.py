"""登录/引导接口的轻量限速（内存实现，单进程有效）。

取舍：
- 键取 (客户端 IP, 用户名)：只用用户名会被「换名喷洒」绕过；只用 IP 会误伤 NAT。
- 采用**递增延迟**而非硬锁：硬锁会被用来定向锁死已知用户名（DoS）。
- 另加全局令牌桶，限制整体尝试速率，防分布式喷洒。
- 一旦改为多 worker，这些状态不再跨进程共享（见 design.md 的扩容前置条件）。
"""
from __future__ import annotations

import threading
import time


class LoginThrottle:
    def __init__(self, threshold: int = 5, window: float = 60.0, max_delay: float = 5.0):
        self._threshold = threshold
        self._window = window
        self._max_delay = max_delay
        self._fails: dict[str, list[float]] = {}
        self._lock = threading.Lock()

    def _prune(self, key: str, now: float) -> list[float]:
        stamps = [t for t in self._fails.get(key, []) if now - t < self._window]
        self._fails[key] = stamps
        return stamps

    def delay_for(self, key: str) -> float:
        now = time.monotonic()
        with self._lock:
            n = len(self._prune(key, now))
        if n < self._threshold:
            return 0.0
        return min(self._max_delay, 0.5 * (n - self._threshold + 1))

    def record_failure(self, key: str) -> None:
        now = time.monotonic()
        with self._lock:
            self._prune(key, now)
            self._fails.setdefault(key, []).append(now)

    def reset(self, key: str) -> None:
        with self._lock:
            self._fails.pop(key, None)


class TokenBucket:
    """全局令牌桶：限制单位时间内的总尝试次数。"""

    def __init__(self, capacity: float = 60.0, refill_per_second: float = 1.0):
        self._capacity = capacity
        self._tokens = capacity
        self._rate = refill_per_second
        self._last = time.monotonic()
        self._lock = threading.Lock()

    def allow(self) -> bool:
        now = time.monotonic()
        with self._lock:
            self._tokens = min(
                self._capacity, self._tokens + (now - self._last) * self._rate
            )
            self._last = now
            if self._tokens < 1:
                return False
            self._tokens -= 1
            return True

    def reset(self) -> None:
        with self._lock:
            self._tokens = self._capacity
            self._last = time.monotonic()


login_throttle = LoginThrottle()
setup_throttle = LoginThrottle()
auth_bucket = TokenBucket()


def reset_rate_limits() -> None:
    """清空所有限速状态（供测试与运维排障使用）。"""
    global login_throttle, setup_throttle
    login_throttle = LoginThrottle()
    setup_throttle = LoginThrottle()
    auth_bucket.reset()