from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def write_text_atomic(path: Path, text: str, *, encoding: str = "utf-8") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    tmp_path.write_text(text, encoding=encoding)
    tmp_path.replace(path)


def write_json_atomic(
    path: Path,
    payload: Any,
    *,
    indent: int = 2,
    ensure_ascii: bool = True,
    encoding: str = "utf-8",
) -> None:
    write_text_atomic(
        path,
        json.dumps(payload, indent=indent, ensure_ascii=ensure_ascii),
        encoding=encoding,
    )
