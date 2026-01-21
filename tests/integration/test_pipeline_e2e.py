"""
DESCRIPTION
-----------
Integration test for the pipeline end-to-end execution path.
This test runs a minimal DAG in a temporary repo_root and verifies final exports exist.
"""


from __future__ import annotations

from pathlib import Path

import yaml

from src.orchestrator.run_pipeline import run_pipeline


def test_pipeline_e2e(tmp_path: Path) -> None:
    #note: Create minimal configs in the temporary repo root so run_pipeline can load them.
    cfg_dir = tmp_path / "configs" / "pipeline"
    cfg_dir.mkdir(parents=True, exist_ok=True)

    (cfg_dir / "dag.yml").write_text("- AG-00\n- AG-01\n", encoding="utf-8")
    (cfg_dir / "id_policy.yml").write_text("key_fields: [entity_type, entity_name]\nprefix: ENT\n", encoding="utf-8")

    case_input = {
        "company_name": "Example GmbH",
        "company_web_domain": "example.com",
        "run_id": "RUN-TEST",
    }

    manifest = run_pipeline(case_input=case_input, run_id="RUN-TEST", repo_root=tmp_path)

    run_root = tmp_path / "artifacts" / "runs" / "RUN-TEST"
    assert (run_root / "exports" / "report.md").exists()
    assert (run_root / "exports" / "entities.json").exists()
    assert manifest["run_id"] == "RUN-TEST"
