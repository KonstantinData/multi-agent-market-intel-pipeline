"""
DESCRIPTION
-----------
RunContext is the single source of truth for deterministic, run_id-based artifact paths.
It resolves all runtime directories (meta/steps/logs/exports) under artifacts/runs/<run_id>/
and is intentionally designed for auditability and testability.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional


#note: RunContext is immutable so that downstream code cannot accidentally mutate run paths mid-run.
@dataclass(frozen=True)
class RunContext:
    """
    #note: Holds the resolved file-system layout for one deterministic pipeline run.
    """

    #note: Repository root can be monkeypatched in tests to redirect artifacts.
    REPO_ROOT: Path = Path(__file__).resolve().parents[2]

    run_id: str = ""
    run_root: Path = Path(".")
    meta_dir: Path = Path(".")
    steps_dir: Path = Path(".")
    logs_dir: Path = Path(".")
    exports_dir: Path = Path(".")

    #note: Create a fully-initialized RunContext and ensure all required directories exist.
    @classmethod
    def create(cls, run_id: str, repo_root: Optional[Path] = None) -> "RunContext":
        """
        #note: Resolve deterministic run folders for the given run_id.

        The canonical layout is:
          <repo_root>/artifacts/runs/<run_id>/
            meta/
            steps/
            logs/
            exports/
        """
        root = repo_root or cls.REPO_ROOT
        run_root = root / "artifacts" / "runs" / run_id

        meta_dir = run_root / "meta"
        steps_dir = run_root / "steps"
        logs_dir = run_root / "logs"
        exports_dir = run_root / "exports"

        meta_dir.mkdir(parents=True, exist_ok=True)
        steps_dir.mkdir(parents=True, exist_ok=True)
        logs_dir.mkdir(parents=True, exist_ok=True)
        exports_dir.mkdir(parents=True, exist_ok=True)

        return cls(
            REPO_ROOT=root,
            run_id=run_id,
            run_root=run_root,
            meta_dir=meta_dir,
            steps_dir=steps_dir,
            logs_dir=logs_dir,
            exports_dir=exports_dir,
        )

    #note: Deterministic path to the JSON registry snapshot persisted after each step.
    @property
    def registry_path(self) -> Path:
        return self.meta_dir / "entity_registry.json"

    #note: Deterministic path to the run manifest metadata file.
    @property
    def manifest_path(self) -> Path:
        return self.meta_dir / "run_manifest.json"

    #note: Deterministic path where the original UI intake payload is stored.
    @property
    def case_input_path(self) -> Path:
        return self.meta_dir / "case_input.json"

    #note: Deterministic directory for a specific step.
    def step_dir(self, step_id: str) -> Path:
        return self.steps_dir / step_id

    #note: Deterministic output path for a specific step.
    def step_output_path(self, step_id: str) -> Path:
        return self.step_dir(step_id) / "output.json"

    #note: Deterministic gatekeeper/validator result path for a specific step.
    def step_validation_path(self, step_id: str) -> Path:
        return self.step_dir(step_id) / "validation.json"
