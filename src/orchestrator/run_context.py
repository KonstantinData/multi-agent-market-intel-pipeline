from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class RunContext:
    run_id: str
    run_root: Path
    meta_dir: Path
    steps_dir: Path
    logs_dir: Path
    exports_dir: Path

    @staticmethod
    def from_run_id(repo_root: Path, run_id: str) -> "RunContext":
        run_root = repo_root / "runs" / run_id
        meta_dir = run_root / "meta"
        steps_dir = run_root / "steps"
        logs_dir = run_root / "logs"
        exports_dir = run_root / "exports"

        meta_dir.mkdir(parents=True, exist_ok=True)
        steps_dir.mkdir(parents=True, exist_ok=True)
        logs_dir.mkdir(parents=True, exist_ok=True)
        exports_dir.mkdir(parents=True, exist_ok=True)

        return RunContext(
            run_id=run_id,
            run_root=run_root,
            meta_dir=meta_dir,
            steps_dir=steps_dir,
            logs_dir=logs_dir,
            exports_dir=exports_dir,
        )
