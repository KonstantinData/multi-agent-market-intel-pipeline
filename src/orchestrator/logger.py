from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path


def utc_ts() -> str:
    return datetime.now(timezone.utc).isoformat()


def log_line(log_path: Path, msg: str) -> None:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    line = f"{utc_ts()} | {msg}\n"
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(line)


def format_relative_path(base: Path, path: Path) -> str:
    try:
        return str(path.resolve().relative_to(base.resolve()))
    except ValueError:
        return path.name
