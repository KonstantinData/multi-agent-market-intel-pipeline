from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path
from typing import Any
from uuid import uuid4

import httpx

from src.orchestrator import run_pipeline
from src.agents.ag10_identity_legal import agent as ag10_agent


class _DummyResponse:
    status_code = 404
    headers: dict[str, Any] = {}
    text = ""


def test_pipeline_end_to_end_smoke(tmp_path: Path, monkeypatch) -> None:
    case_payload = {
        "company_name": "Example Corp",
        "web_domain": "https://example.com",
        "pipeline_version": "abc1234",
    }
    case_path = tmp_path / "case.json"
    case_path.write_text(json.dumps(case_payload), encoding="utf-8")

    run_id = f"smoke-{uuid4().hex[:8]}"
    repo_root = Path(__file__).resolve().parents[2]
    run_root = repo_root / "artifacts" / "runs" / run_id

    monkeypatch.delenv("OPENAI_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setattr(httpx.Client, "get", lambda *args, **kwargs: _DummyResponse())
    monkeypatch.setattr(ag10_agent, "_openai_api_key", lambda: "test-key")
    monkeypatch.setattr(
        ag10_agent,
        "_openai_extract_legal_identity",
        lambda *args, **kwargs: {
            "legal_name": "n/v",
            "legal_form": "n/v",
            "founding_year": "n/v",
            "registration_signals": "n/v",
        },
    )

    argv = [
        "run_pipeline",
        "--run-id",
        run_id,
        "--case-file",
        str(case_path),
        "--pipeline-version",
        "abc1234",
    ]

    try:
        monkeypatch.setattr(sys, "argv", argv)
        run_pipeline.main()

        exports_dir = run_root / "exports"
        report_path = exports_dir / "report.md"
        assert report_path.exists()

        report_text = report_path.read_text(encoding="utf-8")
        assert "## AG-00 — ag00_intake_normalization" in report_text
        assert "## AG-90 — ag90_sales_playbook" in report_text

        required_exports = [
            "entities.json",
            "relations.json",
            "index.json",
            "entities.csv",
            "relations.csv",
            "index.csv",
        ]
        for filename in required_exports:
            path = exports_dir / filename
            assert path.exists()
            assert path.stat().st_size > 0

        entities = json.loads((exports_dir / "entities.json").read_text())
        assert any(entity["entity_id"] == "TGT-001" for entity in entities)

        validator_path = run_root / "steps" / "AG-00" / "validator.json"
        validator_payload = json.loads(validator_path.read_text())
        assert validator_payload["ok"] is True
    finally:
        if run_root.exists():
            shutil.rmtree(run_root)
