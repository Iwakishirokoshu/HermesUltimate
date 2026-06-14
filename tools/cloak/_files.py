from __future__ import annotations

import os
import stat
from pathlib import Path


PRIVATE_DIR_MODE = stat.S_IRWXU
PRIVATE_FILE_MODE = stat.S_IRUSR | stat.S_IWUSR


def ensure_private_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    try:
        os.chmod(path, PRIVATE_DIR_MODE)
    except OSError:
        pass
    return path


def restrict_file(path: Path) -> Path:
    try:
        os.chmod(path, PRIVATE_FILE_MODE)
    except OSError:
        pass
    return path


def write_private_bytes(path: Path, content: bytes) -> Path:
    ensure_private_dir(path.parent)
    path.write_bytes(content)
    return restrict_file(path)


def write_private_text(path: Path, content: str, *, encoding: str = "utf-8") -> Path:
    ensure_private_dir(path.parent)
    path.write_text(content, encoding=encoding)
    return restrict_file(path)
