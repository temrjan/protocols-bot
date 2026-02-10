from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from loguru import logger


@dataclass
class LocalStorageConfig:
    root: Path
    soft_limit_ratio: float = 0.8


_config: Optional[LocalStorageConfig] = None


def configure(config: LocalStorageConfig) -> None:
    global _config
    root = config.root
    root.mkdir(parents=True, exist_ok=True)
    _config = LocalStorageConfig(root=root, soft_limit_ratio=config.soft_limit_ratio)
    logger.debug("Local storage configured at {path}", path=root)


def _require_config() -> LocalStorageConfig:
    if _config is None:
        raise RuntimeError("Local storage is not configured")
    return _config


def _ensure_capacity(root: Path) -> None:
    usage = os.statvfs(root)
    capacity = usage.f_blocks * usage.f_frsize
    available = usage.f_bavail * usage.f_frsize
    used = capacity - available
    ratio = used / capacity if capacity else 0
    if ratio >= _config.soft_limit_ratio:  # type: ignore[union-attr]
        percent = int(ratio * 100)
        raise RuntimeError(f"Storage usage is above soft limit ({percent}% used)")


ALLOWED_MIME_EXTENSIONS = {
    "application/pdf": {".pdf"},
    "image/jpeg": {".jpg", ".jpeg"},
    "image/jpg": {".jpg", ".jpeg"},
}


def save_bytes(key: str, data: bytes, mime: str = "application/pdf") -> Path:
    config = _require_config()
    storage_path = sanitize_key(config.root, key)
    extension = storage_path.suffix.lower()
    if mime not in ALLOWED_MIME_EXTENSIONS:
        raise ValueError("Unsupported MIME type")
    if extension not in ALLOWED_MIME_EXTENSIONS[mime]:
        raise ValueError("File extension does not match MIME type")
    _ensure_capacity(config.root)
    storage_path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = storage_path.with_suffix(storage_path.suffix + ".tmp")
    temp_path.write_bytes(data)
    temp_path.replace(storage_path)
    logger.info("Stored protocol at {path}", path=storage_path)
    return storage_path


def open_path(key: str) -> Path:
    config = _require_config()
    storage_path = sanitize_key(config.root, key)
    if not storage_path.exists():
        raise FileNotFoundError(f"Protocol not found: {key}")
    return storage_path


def exists(key: str) -> bool:
    config = _require_config()
    storage_path = sanitize_key(config.root, key)
    return storage_path.exists()


def get_size(key: str) -> Optional[int]:
    config = _require_config()
    storage_path = sanitize_key(config.root, key)
    if not storage_path.exists():
        return None
    return storage_path.stat().st_size


def sanitize_key(root: Path, key: str) -> Path:
    if ".." in key or key.startswith("/"):
        raise ValueError("Invalid storage key")
    safe_key = key.replace("\\", "/")
    path = root / safe_key
    normalized = path.resolve(strict=False)
    if not str(normalized).startswith(str(root.resolve())):
        raise ValueError("Storage key escapes root directory")
    return normalized


__all__ = [
    "LocalStorageConfig",
    "configure",
    "save_bytes",
    "open_path",
    "exists",
    "get_size",
    "sanitize_key",
]
