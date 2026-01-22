"""
    DESCRIPTION
    -----------
    ArtifactStore provides atomic, deterministic file IO for run artifacts.
All writes use a tmp file + replace to avoid half-written artifacts.
    """

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict


#note: Ensure parent directories exist before writing artifacts.
def _ensure_parent_dir(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


#note: Write text atomically (tmp -> replace) to guarantee consistent artifacts.
def atomic_write_text(path: Path, content: str) -> None:
    _ensure_parent_dir(path)
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    tmp_path.write_text(content, encoding="utf-8")
    os.replace(tmp_path, path)


#note: Write JSON atomically with deterministic formatting (sorted keys + stable indentation).
def atomic_write_json(path: Path, payload: Any) -> None:
    text = json.dumps(payload, ensure_ascii=True, sort_keys=True, indent=2)
    atomic_write_text(path, text + "\\n")


#note: Read JSON with a strict failure mode (invalid JSON is a hard error).
def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


#note: Small helper used by exporters to compute deterministic sha256 for manifesting.
def sha256_bytes(data: bytes) -> str:
    import hashlib

    return hashlib.sha256(data).hexdigest()


#note: Compute sha256 hash of a file for manifest integrity checks.
def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


#note: Build a minimal manifest entry for an artifact output.
def build_manifest_entry(path: Path, base_dir: Path) -> Dict[str, Any]:
    rel = str(path.relative_to(base_dir)).replace("\\", "/")
    data = path.read_bytes()
    return {
        "path": rel,
        "bytes": len(data),
        "sha256": sha256_bytes(data),
    }
