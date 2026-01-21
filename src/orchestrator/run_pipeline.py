from __future__ import annotations

import argparse
import json
import os
import shutil
from pathlib import Path
from typing import Any, Dict

from src.agents.ag00_intake_normalization.agent import AgentAG00IntakeNormalization
from src.agents.ag01_source_registry.agent import AgentAG01SourceRegistry
from src.agents.ag10_identity_legal.agent import AgentAG10IdentityLegal
from src.agents.ag11_locations_sites.agent import AgentAG11LocationsSites
from src.agents.ag20_company_size.agent import AgentAG20CompanySize
from src.agents.ag21_financial_signals.agent import AgentAG21FinancialSignals
from src.agents.ag30_portfolio.agent import AgentAG30Portfolio
from src.agents.ag31_markets_focus.agent import AgentAG31MarketsFocus
from src.agents.ag40_target_customers.agent import AgentAG40TargetCustomers
from src.agents.ag41_peer_discovery.agent import AgentAG41PeerDiscovery
from src.agents.ag42_customers_of_manufacturers.agent import (
    AgentAG42CustomersOfManufacturers,
)
from src.agents.ag70_supply_chain_tech.agent import AgentAG70SupplyChainTech
from src.agents.ag71_supply_chain_risks.agent import AgentAG71SupplyChainRisks
from src.agents.ag72_sustainability_circular.agent import (
    AgentAG72SustainabilityCircular,
)
from src.agents.ag81_industry_trends.agent import AgentAG81IndustryTrends
from src.agents.ag82_trade_fairs_events.agent import AgentAG82TradeFairsEvents
from src.agents.ag83_associations_memberships.agent import (
    AgentAG83AssociationsMemberships,
)
from src.agents.ag90_sales_playbook.agent import AgentAG90SalesPlaybook
from src.exporters.report_builder import build_report
from src.orchestrator.logger import log_line
from src.orchestrator.run_context import RunContext
from src.validator.contract_validator import (
    load_step_contracts,
    validate_ag00_output,
    validate_ag01_output,
    validate_ag10_output,
    validate_ag11_output,
    validate_ag20_output,
    validate_research_output,
)
from src.agent_common.file_utils import write_json_atomic, write_text_atomic
from src.agent_common.step_meta import utc_now_iso
from src.orchestrator.dag_loader import StepNode, load_dag

STEP_AGENT_REGISTRY = {
    "AG-00": AgentAG00IntakeNormalization,
    "AG-01": AgentAG01SourceRegistry,
    "AG-10": AgentAG10IdentityLegal,
    "AG-11": AgentAG11LocationsSites,
    "AG-20": AgentAG20CompanySize,
    "AG-21": AgentAG21FinancialSignals,
    "AG-30": AgentAG30Portfolio,
    "AG-31": AgentAG31MarketsFocus,
    "AG-40": AgentAG40TargetCustomers,
    "AG-41": AgentAG41PeerDiscovery,
    "AG-42": AgentAG42CustomersOfManufacturers,
    "AG-70": AgentAG70SupplyChainTech,
    "AG-71": AgentAG71SupplyChainRisks,
    "AG-72": AgentAG72SustainabilityCircular,
    "AG-81": AgentAG81IndustryTrends,
    "AG-82": AgentAG82TradeFairsEvents,
    "AG-83": AgentAG83AssociationsMemberships,
    "AG-90": AgentAG90SalesPlaybook,
}

STEPS_REQUIRING_META = {"AG-01", "AG-10", "AG-11", "AG-20"}


def _resolve_pipeline_version(
    case_input: Dict[str, Any], pipeline_version_override: str | None
) -> str:
    candidates = (
        pipeline_version_override,
        os.getenv("PIPELINE_VERSION"),
        case_input.get("pipeline_version"),
    )
    for candidate in candidates:
        if isinstance(candidate, str) and candidate.strip():
            return candidate.strip()
    return ""


def read_case_input(
    case_file: str,
    *,
    pipeline_version_override: str | None,
    log_path: Path | None = None,
) -> Dict[str, Any]:
    p = Path(case_file)
    case_input = json.loads(p.read_text(encoding="utf-8"))
    pipeline_version = _resolve_pipeline_version(case_input, pipeline_version_override)
    if not pipeline_version:
        message = (
            "pipeline_version is required; set --pipeline-version or PIPELINE_VERSION."
        )
        if log_path is not None:
            log_line(log_path, message)
        raise SystemExit(message)
    case_input["pipeline_version"] = pipeline_version
    return case_input


def write_json(path: Path, payload: Dict[str, Any]) -> None:
    write_json_atomic(path, payload)


def _log_skipped_steps(
    log_path: Path, failed_step_id: str, pipeline_steps: list[str]
) -> None:
    if failed_step_id not in pipeline_steps:
        return

    failed_index = pipeline_steps.index(failed_step_id)
    remaining_steps = pipeline_steps[failed_index + 1 :]
    if not remaining_steps:
        return

    for step_id in remaining_steps:
        log_line(
            log_path, f"Skipping {step_id} due to {failed_step_id} gatekeeper failure"
        )


def _require_step_meta(
    output_payload: Dict[str, Any], step_id: str, log_path: Path
) -> Dict[str, Any]:
    step_meta = output_payload.get("step_meta")
    if not isinstance(step_meta, dict):
        log_line(log_path, f"{step_id} output missing step_meta")
        raise SystemExit(3)
    if step_meta.get("step_id") != step_id:
        log_line(
            log_path,
            f"{step_id} output step_meta.step_id mismatch: {step_meta.get('step_id')}",
        )
        raise SystemExit(3)
    run_id = step_meta.get("run_id")
    if not isinstance(run_id, str) or not run_id.strip():
        log_line(log_path, f"{step_id} output missing step_meta.run_id")
        raise SystemExit(3)
    pipeline_version = step_meta.get("pipeline_version")
    if not isinstance(pipeline_version, str) or not pipeline_version.strip():
        log_line(log_path, f"{step_id} output missing step_meta.pipeline_version")
        raise SystemExit(3)
    return step_meta


def _assert_validator_consistency(
    validator_payload: Dict[str, Any],
    step_meta: Dict[str, Any],
    step_id: str,
    log_path: Path,
) -> None:
    mismatches = []
    for field in ("step_id", "run_id", "pipeline_version"):
        if validator_payload.get(field) != step_meta.get(field):
            mismatches.append(field)
    if mismatches:
        log_line(
            log_path,
            f"{step_id} validator consistency check failed for fields: {', '.join(mismatches)}",
        )
        raise SystemExit(3)


def build_validator_payload(
    *,
    validation_result: Any,
    output_payload: Dict[str, Any],
    log_path: Path,
) -> Dict[str, Any]:
    step_id = validation_result.step_id
    step_meta = _require_step_meta(output_payload, step_id, log_path)
    validator_payload = {
        "step_id": step_id,
        "run_id": step_meta["run_id"],
        "pipeline_version": step_meta["pipeline_version"],
        "validated_at_utc": utc_now_iso(),
        "ok": validation_result.ok,
        "errors": [
            {"code": e.code, "message": e.message, "path": e.path}
            for e in validation_result.errors
        ],
        "warnings": [
            {"code": w.code, "message": w.message, "path": w.path}
            for w in validation_result.warnings
        ],
    }
    _assert_validator_consistency(validator_payload, step_meta, step_id, log_path)
    return validator_payload


def _build_agent_kwargs(
    *,
    step_id: str,
    case_input: Dict[str, Any],
    meta_payloads: Dict[str, Any],
    log_path: Path,
) -> Dict[str, Any]:
    if step_id in STEPS_REQUIRING_META:
        case_normalized = meta_payloads.get("case_normalized")
        target_stub = meta_payloads.get("target_entity_stub")
        if not isinstance(case_normalized, dict) or not isinstance(target_stub, dict):
            log_line(log_path, f"{step_id} missing required meta payloads")
            raise SystemExit(3)
        return {
            "case_input": case_input,
            "meta_case_normalized": case_normalized,
            "meta_target_entity_stub": target_stub,
        }
    return {"case_input": case_input}


def _validate_step_output(
    *,
    step_id: str,
    output_payload: Dict[str, Any],
    contract: Dict[str, Any],
    meta_payloads: Dict[str, Any],
) -> Any:
    if step_id == "AG-00":
        return validate_ag00_output(output_payload, contract)
    if step_id == "AG-01":
        return validate_ag01_output(output_payload, contract)
    if step_id == "AG-10":
        case_normalized = meta_payloads.get("case_normalized") or {}
        return validate_ag10_output(
            output_payload,
            contract,
            expected_entity_key=str(case_normalized.get("entity_key", "")),
            expected_domain=str(case_normalized.get("web_domain_normalized", "")),
        )
    if step_id == "AG-11":
        return validate_ag11_output(output_payload, contract)
    if step_id == "AG-20":
        case_normalized = meta_payloads.get("case_normalized") or {}
        return validate_ag20_output(
            output_payload,
            contract,
            expected_entity_key=str(case_normalized.get("entity_key", "")),
            expected_domain=str(case_normalized.get("web_domain_normalized", "")),
        )
    return validate_research_output(output_payload, contract)


def _load_pipeline_dag(repo_root: Path) -> list[StepNode]:
    dag = load_dag(str(repo_root / "configs/pipeline/dag.yml"))
    if not dag.nodes:
        raise SystemExit("pipeline DAG is empty")
    return dag.nodes


def _next_backup_path(run_root: Path) -> Path:
    timestamp = (
        utc_now_iso()
        .replace(":", "")
        .replace("-", "")
        .replace("T", "_")
        .replace("Z", "")
    )
    candidate = run_root.with_name(f"{run_root.name}.bak-{timestamp}")
    if not candidate.exists():
        return candidate
    counter = 1
    while True:
        numbered = run_root.with_name(f"{run_root.name}.bak-{timestamp}-{counter}")
        if not numbered.exists():
            return numbered
        counter += 1


def _prepare_run_root(
    *,
    repo_root: Path,
    run_id: str,
    overwrite: bool,
    backup_existing: bool,
    case_file: Path | None = None,
) -> Path:
    run_root = repo_root / "artifacts" / "runs" / run_id
    if run_root.exists() and any(run_root.iterdir()):
        if overwrite:
            shutil.rmtree(run_root)
        elif backup_existing:
            backup_root = _next_backup_path(run_root)
            shutil.move(str(run_root), str(backup_root))
        elif case_file and case_file.exists() and run_root in case_file.parents:
            return run_root
        else:
            raise SystemExit(
                "Run directory already exists and is not empty. "
                "Use --overwrite to replace or --backup-existing to archive."
            )
    return run_root


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--case-file", required=True)
    parser.add_argument("--pipeline-version")
    run_dir_group = parser.add_mutually_exclusive_group()
    run_dir_group.add_argument(
        "--overwrite",
        action="store_true",
        help="Replace an existing non-empty run directory.",
    )
    run_dir_group.add_argument(
        "--backup-existing",
        action="store_true",
        help="Archive an existing non-empty run directory before running.",
    )
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parents[2]
    case_file_path = Path(args.case_file).resolve()
    _prepare_run_root(
        repo_root=repo_root,
        run_id=args.run_id,
        overwrite=args.overwrite,
        backup_existing=args.backup_existing,
        case_file=case_file_path,
    )
    ctx = RunContext.from_run_id(repo_root=repo_root, run_id=args.run_id)

    log_path = ctx.logs_dir / "pipeline.log"
    log_line(log_path, f"PIPELINE START run_id={ctx.run_id}")

    case_input = read_case_input(
        str(case_file_path),
        pipeline_version_override=args.pipeline_version,
        log_path=log_path,
    )
    case_input["run_id"] = ctx.run_id
    log_line(
        log_path, f"Loaded case_file run_id={ctx.run_id} file={case_file_path.name}"
    )

    step_contracts = load_step_contracts(
        str(repo_root / "configs/pipeline/step_contracts.yml")
    )
    dag_nodes = _load_pipeline_dag(repo_root)
    pipeline_steps = [node.step_id for node in dag_nodes]
    meta_payloads: Dict[str, Any] = {}
    completed_steps: set[str] = set()

    for node in dag_nodes:
        step_id = node.step_id
        if step_id not in STEP_AGENT_REGISTRY:
            log_line(log_path, f"Missing agent registry entry for {step_id}")
            raise SystemExit(1)
        if step_id not in step_contracts:
            log_line(log_path, f"Missing contract entry for {step_id}")
            raise SystemExit(1)
        missing_deps = [dep for dep in node.depends_on if dep not in completed_steps]
        if missing_deps:
            log_line(
                log_path, f"{step_id} missing dependencies: {', '.join(missing_deps)}"
            )
            raise SystemExit(1)

        step_dir = ctx.steps_dir / step_id
        step_dir.mkdir(parents=True, exist_ok=True)
        agent = STEP_AGENT_REGISTRY[step_id]()
        log_line(log_path, f"Running {step_id} agent")

        agent_kwargs = _build_agent_kwargs(
            step_id=step_id,
            case_input=case_input,
            meta_payloads=meta_payloads,
            log_path=log_path,
        )
        agent_result = agent.run(**agent_kwargs)

        if not agent_result.ok:
            write_json(step_dir / "agent_error.json", agent_result.output)
            log_line(log_path, f"{step_id} agent self-validation FAILED")
            raise SystemExit(2)

        output_path = step_dir / "output.json"
        write_json(output_path, agent_result.output)
        log_line(log_path, f"{step_id} output written run_id={ctx.run_id}")

        contract = step_contracts[step_id]
        vr = _validate_step_output(
            step_id=step_id,
            output_payload=agent_result.output,
            contract=contract,
            meta_payloads=meta_payloads,
        )
        validator_payload = build_validator_payload(
            validation_result=vr,
            output_payload=agent_result.output,
            log_path=log_path,
        )

        write_json(step_dir / "validator.json", validator_payload)
        log_line(log_path, f"{step_id} gatekeeper ok={vr.ok}")

        if not vr.ok:
            log_line(log_path, f"PIPELINE STOP ({step_id} contract validation failed)")
            _log_skipped_steps(log_path, step_id, pipeline_steps)
            raise SystemExit(3)

        if step_id == "AG-00":
            meta_payloads["case_normalized"] = agent_result.output["case_normalized"]
            meta_payloads["target_entity_stub"] = agent_result.output[
                "target_entity_stub"
            ]
            write_json(
                ctx.meta_dir / "case_normalized.json", meta_payloads["case_normalized"]
            )
            write_json(
                ctx.meta_dir / "target_entity_stub.json",
                meta_payloads["target_entity_stub"],
            )

        completed_steps.add(step_id)

    try:
        report = build_report(ctx)
        report_path = ctx.exports_dir / "report.md"
        write_text_atomic(report_path, report)
        relative_report_path = report_path.relative_to(ctx.run_root)
        log_line(log_path, f"Report written path={relative_report_path.as_posix()}")
    except Exception as exc:
        log_line(log_path, f"PIPELINE STOP (reporting failed: {exc})")
        raise SystemExit(4) from exc

    log_line(
        log_path,
        f"PIPELINE END ({', '.join(pipeline_steps)} completed successfully)",
    )


if __name__ == "__main__":
    main()
