"""
    DESCRIPTION
    -----------
    run_pipeline is the UI/CLI entrypoint for executing the full pipeline DAG.

Responsibilities:
- Create a deterministic RunContext (artifacts/runs/<run_id>/...)
- Load DAG + configs
- Execute each step, persisting step outputs and validator results
- Maintain and persist a shared EntityRegistry snapshot after every step
- Produce final exports/report.md and exports/entities.json
    """

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any, Dict, Optional
import uuid

import yaml

from src.agents.common.base_agent import AgentResult
from src.orchestrator.artifact_store import atomic_write_json, atomic_write_text, build_manifest_entry
from src.orchestrator.dag_loader import load_dag
from src.orchestrator.run_context import RunContext
from src.orchestrator.step_registry import build_agent
from src.registry.entity_registry import EntityRegistry
from src.validator.step_validator import validate_step_output
from src.exporters.expose_exporter import build_entities_export, build_report_markdown


#note: Generate a run_id when the UI did not provide one (still deterministic within the run).
def _generate_run_id() -> str:
    return f"run_{uuid.uuid4().hex[:12]}"


#note: Load YAML configs from the repository.
def _load_yaml(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


#note: Execute a pipeline run and return a summary dict (also written as manifest).
def run_pipeline(
    *,
    case_input: Dict[str, Any],
    run_id: Optional[str] = None,
    repo_root: Optional[Path] = None,
) -> Dict[str, Any]:
    """
    #note: Headless entrypoint for tests and UI integration.
    """
    rid = str(run_id or case_input.get("run_id") or "").strip() or _generate_run_id()
    case_input = dict(case_input)
    case_input["run_id"] = rid

    ctx = RunContext.create(run_id=rid, repo_root=repo_root)

    #note: Persist canonical intake payload for auditability.
    atomic_write_json(ctx.case_input_path, case_input)

    #note: Load configs required for deterministic registry behavior.
    id_policy = _load_yaml(ctx.REPO_ROOT / "configs" / "pipeline" / "id_policy.yml") or {"key_fields": [], "prefix": "ENT"}
    registry = EntityRegistry(id_policy=id_policy, namespace=rid)

    dag = load_dag(ctx.REPO_ROOT / "configs" / "pipeline" / "dag.yml")

    #note: Meta artifacts propagated from AG-00 to all later steps.
    meta_case_normalized: Dict[str, Any] = {}
    meta_target_entity_stub: Dict[str, Any] = {}

    steps_summary = []

    for step_id in dag.steps_order:
        step_dir = ctx.step_dir(step_id)
        step_dir.mkdir(parents=True, exist_ok=True)

        agent = build_agent(step_id)

        #note: Provide the cumulative shared state snapshot to every agent deterministically.
        registry_snapshot = registry.snapshot()

        #note: Run agent with a flexible signature (agents may ignore optional args).
        result = _invoke_agent(
            agent=agent,
            case_input=case_input,
            meta_case_normalized=meta_case_normalized,
            meta_target_entity_stub=meta_target_entity_stub,
            registry_snapshot=registry_snapshot,
        )

        #note: Persist step output as the canonical audit artifact.
        atomic_write_json(ctx.step_output_path(step_id), result.output)

        #note: Validate output (hard fail if validator returns ok=False).
        validation = validate_step_output(step_id=step_id, output=result.output)
        atomic_write_json(ctx.step_validation_path(step_id), validation)

        if not validation.get("ok", False):
            #note: Persist registry snapshot even on failure to support debugging.
            atomic_write_json(ctx.registry_path, registry.snapshot())
            raise RuntimeError(f"Gatekeeper FAIL at {step_id}: {validation.get('errors', [])}")

        #note: Update shared state registry.
        registry.ingest_step_output(result.output)
        atomic_write_json(ctx.registry_path, registry.snapshot())

        #note: Capture AG-00 artifacts used by subsequent steps.
        if step_id == "AG-00":
            meta_case_normalized = dict(result.output.get("case_normalized") or {})
            #note: TGT-001 is the canonical target entity stub by convention.
            meta_target_entity_stub = _extract_target_stub(result.output) or {}

        steps_summary.append(
            {
                "step_id": step_id,
                "ok": True,
                "output_path": str(ctx.step_output_path(step_id).relative_to(ctx.run_root)).replace("\\", "/"),
                "validation_path": str(ctx.step_validation_path(step_id).relative_to(ctx.run_root)).replace("\\", "/"),
            }
        )

    #note: Final exports (Exposé artifacts) are derived from the shared registry snapshot.
    entities_payload = build_entities_export(registry.snapshot())
    atomic_write_json(ctx.exports_dir / "entities.json", entities_payload)

    report_md = build_report_markdown(registry.snapshot())
    atomic_write_text(ctx.exports_dir / "report.md", report_md)

    #note: Persist run-level manifest for quick verification and CI.
    outputs = [
        build_manifest_entry(ctx.exports_dir / "entities.json", ctx.run_root),
        build_manifest_entry(ctx.exports_dir / "report.md", ctx.run_root),
    ]
    manifest = {
        "run_id": rid,
        "steps_executed": [s["step_id"] for s in steps_summary],
        "steps": steps_summary,
        "exports": outputs,
    }
    atomic_write_json(ctx.manifest_path, manifest)

    return manifest


#note: Extract the canonical target company stub from AG-00 outputs.
def _extract_target_stub(output: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    entities = output.get("entities_delta") or []
    for ent in entities:
        if isinstance(ent, dict) and str(ent.get("entity_id")) == "TGT-001":
            return ent
    return None


#note: Invoke an agent while supporting legacy run() signatures.
#note: Invoke an agent while supporting legacy run() signatures.
def _invoke_agent(
    *,
    agent: Any,
    case_input: Dict[str, Any],
    meta_case_normalized: Dict[str, Any],
    meta_target_entity_stub: Dict[str, Any],
    registry_snapshot: Dict[str, Any],
) -> AgentResult:
    """
    #note: This function allows incremental migration of agents without a big-bang refactor.

    IMPORTANT:
    - We inspect the *bound* run() method, so `self` is NOT part of the signature length.
    """
    import inspect

    sig = inspect.signature(agent.run)
    params = list(sig.parameters.keys())

    #note: 1 arg  -> run(case_input)
    if len(params) == 1:
        return agent.run(case_input)

    #note: 3 args -> run(case_input, meta_case_normalized, meta_target_entity_stub)
    if len(params) == 3:
        return agent.run(case_input, meta_case_normalized, meta_target_entity_stub)

    #note: 4+ args -> run(..., registry_snapshot) (agents may ignore it)
    if len(params) >= 4:
        return agent.run(case_input, meta_case_normalized, meta_target_entity_stub, registry_snapshot)

    #note: Fallback for unusual signatures.
    return agent.run(case_input)


#note: CLI entrypoint used by Streamlit (python -m src.orchestrator.run_pipeline ...).
def main() -> int:
    parser = argparse.ArgumentParser(description="Run the market-intel pipeline for one case_input JSON.")
    parser.add_argument("--run-id", dest="run_id", required=False, help="Deterministic run_id for artifacts/runs/<run_id>/")
    parser.add_argument("--case-file", dest="case_file", required=True, help="Path to a JSON file containing case_input.")
    args = parser.parse_args()

    case_path = Path(args.case_file).expanduser().resolve()
    case_input = yaml.safe_load(case_path.read_text(encoding="utf-8"))
    if not isinstance(case_input, dict):
        raise ValueError("case_file must contain a JSON/YAML object")

    manifest = run_pipeline(case_input=case_input, run_id=args.run_id)
    print(yaml.safe_dump(manifest, sort_keys=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
