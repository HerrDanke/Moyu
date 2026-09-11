"""应用配置：从环境变量读取，支持测试注入。"""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass
class Settings:
    port: int = 8000
    data_dir: Path = Path("./data")
    novel_dir: Path = Path("./novels")
    static_dir: Path = Path("./frontend/dist")
    typing_speed: float = 1.0
    access_password: str = ""
    secret_key: str = "dev-secret-change-me"
    cookie_secure: bool = False  # 走 HTTPS 时设为 True
    max_upload_bytes: int = 100 * 1024 * 1024  # 100MB
    max_chapter_chars: int = 100_000  # 单章上限，超出再拆
    fallback_chapter_chars: int = 3000  # 无章节分隔时按字数兜底
    chunk_sentences: int = 3  # 每批推送句数
    stream_min_delay: float = 0.6
    stream_max_delay: float = 1.4
    thinking_delay: float = 1.5  # 思考光标停顿
    max_input_chars: int = 500  # 指令输入长度上限（防 ReDoS）

    @property
    def db_path(self) -> Path:
        return self.data_dir / "moyu.sqlite3"

    def ensure_dirs(self) -> None:
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.novel_dir.mkdir(parents=True, exist_ok=True)

    @classmethod
    def from_env(cls) -> "Settings":
        def _path(key: str, default: str) -> Path:
            return Path(os.environ.get(key, default)).resolve()

        return cls(
            port=int(os.environ.get("PORT", "8000")),
            data_dir=_path("DATA_DIR", "./data"),
            novel_dir=_path("NOVEL_DIR", "./novels"),
            static_dir=_path("STATIC_DIR", "./frontend/dist"),
            typing_speed=float(os.environ.get("TYPING_SPEED", "1.0")),
            access_password=os.environ.get("ACCESS_PASSWORD", ""),
            secret_key=os.environ.get("SECRET_KEY", "dev-secret-change-me"),
            cookie_secure=os.environ.get("COOKIE_SECURE", "").lower() in {"1", "true", "yes"},
            max_upload_bytes=int(
                os.environ.get("MAX_UPLOAD_BYTES", str(100 * 1024 * 1024))
            ),
        )


_settings: Settings | None = None


def get_settings() -> Settings:
    global _settings
    if _settings is None:
        _settings = Settings.from_env()
    return _settings


def set_settings(settings: Settings) -> None:
    """供测试注入。"""
    global _settings
    _settings = settings