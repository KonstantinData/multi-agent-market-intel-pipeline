# PATH: src/orchestrator/run_pipeline.py
# ACTION: REPLACE

from __future__ import annotations

import hashlib
import json
import os
from typing import Any, Dict, Optional

from src.registry.entity_registry import EntityRegistry


def _atomic_write_text(path: str, content: str) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = f"{path}.tmp"
    with open(tmp, "w", encoding="utf-8", newline="\n") as f:
        f.write(content)
    os.replace(tmp, path)


def _atomic_write_json(path: str, obj: Any) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = f"{path}.tmp"
    with open(tmp, "w", encoding="utf-8", newline="\n") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2, sort_keys=True)
    os.replace(tmp, path)


def _default_run_id(case: Dict[str, Any]) -> str:
    raw = json.dumps(case, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:12]


def run_pipeline(
    case: Dict[str, Any],
    *,
    run_id: Optional[str] = None,
    repo_root: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Deterministic headless pipeline entry point.

    Must produce:
      artifacts/runs/<run_id>/exports/report.md
      artifacts/runs/<run_id>/exports/entities.json
    """
    if not isinstance(case, dict):
        raise TypeError("case must be a dict")

    run_id = run_id or _default_run_id(case)
    repo_root = repo_root or os.getcwd()

    run_dir = os.path.join(repo_root, "artifacts", "runs", run_id)
    exports_dir = os.path.join(run_dir, "exports")

    registry = EntityRegistry(namespace="run")

    # minimal deterministic target entity derived from case
    target_entity: Dict[str, Any] = {
        "type": "target_company",
        "legal_name": case.get("company_name") or case.get("legal_name") or "n/v",
        "domain": case.get("company_domain") or case.get("domain") or "n/v",
        "website": case.get("company_website") or case.get("website") or "n/v",
    }
    registry.add_entities([target_entity])

    entities_path = os.path.join(exports_dir, "entities.json")
    report_path = os.path.join(exports_dir, "report.md")

    _atomic_write_json(entities_path, registry.to_export_payload())

    report_md = "\n".join(
        [
            "# Exposé",
            "",
            "## Run Metadata",
            f"- run_id: `{run_id}`",
            "",
            "## Entities",
            f"- total_entities: {len(registry.export_entities())}",
            "",
        ]
    )
    _atomic_write_text(report_path, report_md)

    return {
        "run_id": run_id,
        "run_dir": run_dir,
        "exports_dir": exports_dir,
        "report_path": report_path,
        "entities_path": entities_path,
    }


__all__ = ["run_pipeline"]
