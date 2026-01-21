"""Simple DoD verification script.

This script checks that for each run directory under artifacts/runs/, the
required subdirectories and files exist according to the DoD checklist.
It can be extended with more checks as needed.
"""
from pathlib import Path
import sys
import json


def verify_run(run_dir: Path) -> bool:
    success = True
    required_subdirs = ["meta", "steps", "logs", "exports"]
    for sub in required_subdirs:
        if not (run_dir / sub).exists():
            print(f"Missing directory: {run_dir / sub}")
            success = False
    exports = run_dir / "exports"
    if not (exports / "entities.json").exists():
        print(f"Missing entities.json in {exports}")
        success = False
    if not (exports / "report.md").exists():
        print(f"Missing report.md in {exports}")
        success = False
    meta = run_dir / "meta"
    if not (meta / "entity_registry.json").exists():
        print(f"Missing entity_registry.json in {meta}")
        success = False
    return success


def main() -> int:
    artifacts_root = Path("artifacts") / "runs"
    if not artifacts_root.exists():
        print("No runs directory found")
        return 1
    success = True
    for run_dir in artifacts_root.iterdir():
        if run_dir.is_dir():
            result = verify_run(run_dir)
            success = success and result
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())