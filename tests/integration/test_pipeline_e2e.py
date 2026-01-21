"""Integration test for the entire pipeline."""
import json
from pathlib import Path

from src.orchestrator.run_pipeline import run_pipeline


def test_pipeline_e2e(tmp_path: Path, monkeypatch):
    # Patch RunContext root to temporary directory
    from src.orchestrator.run_context import RunContext
    monkeypatch.setattr(RunContext, "REPO_ROOT", tmp_path)

    run_id = "RUN-TEST"
    run_pipeline(run_id)

    run_root = tmp_path / "artifacts" / "runs" / run_id
    exports_dir = run_root / "exports"
    assert (exports_dir / "entities.json").exists()
    assert (exports_dir / "report.md").exists()

    entities = json.loads((exports_dir / "entities.json").read_text())
    assert isinstance(entities, list)

    report_content = (exports_dir / "report.md").read_text()
    assert report_content.startswith(f"# Market Intelligence Report for {run_id}")