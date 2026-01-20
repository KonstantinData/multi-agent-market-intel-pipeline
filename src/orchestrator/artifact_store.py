from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class ArtifactStore:
    """Writes artifacts to the run directory with atomic writes."""

    run_root: Path

    def resolve(self, relative_path: str) -> Path:
        return self.run_root / relative_path

    def write_json(self, relative_path: str, payload: Any) -> Path:
        path = self.resolve(relative_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp_path = path.with_suffix(path.suffix + ".tmp")
        tmp_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        tmp_path.replace(path)
        return path

    def read_json(self, relative_path: str) -> Any:
        path = self.resolve(relative_path)
        return json.loads(path.read_text(encoding="utf-8"))
