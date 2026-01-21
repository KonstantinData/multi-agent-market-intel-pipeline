from __future__ import annotations

import argparse
import json
import os
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
from src.agents.ag42_customers_of_manufacturers.agent import AgentAG42CustomersOfManufacturers
from src.agents.ag70_supply_chain_tech.agent import AgentAG70SupplyChainTech
from src.agents.ag71_supply_chain_risks.agent import AgentAG71SupplyChainRisks
from src.agents.ag72_sustainability_circular.agent import AgentAG72SustainabilityCircular
from src.agents.ag81_industry_trends.agent import AgentAG81IndustryTrends
from src.agents.ag82_trade_fairs_events.agent import AgentAG82TradeFairsEvents
from src.agents.ag83_associations_memberships.agent import AgentAG83AssociationsMemberships
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
from src.agent_common.step_meta import utc_now_iso

PIPELINE_STEP_ORDER = [
    "AG-00",
    "AG-01",
    "AG-10",
    "AG-11",
    "AG-20",
    "AG-21",
    "AG-30",
    "AG-31",
    "AG-40",
    "AG-41",
    "AG-42",
    "AG-70",
    "AG-71",
    "AG-72",
    "AG-81",
    "AG-82",
    "AG-83",
    "AG-90",
]


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
    case_file: str, *, pipeline_version_override: str | None, log_path: Path | None = None
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
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _log_skipped_steps(log_path: Path, failed_step_id: str) -> None:
    if failed_step_id not in PIPELINE_STEP_ORDER:
        return

    failed_index = PIPELINE_STEP_ORDER.index(failed_step_id)
    remaining_steps = PIPELINE_STEP_ORDER[failed_index + 1 :]
    if not remaining_steps:
        return

    for step_id in remaining_steps:
        log_line(log_path, f"Skipping {step_id} due to {failed_step_id} gatekeeper failure")


def _require_step_meta(output_payload: Dict[str, Any], step_id: str, log_path: Path) -> Dict[str, Any]:
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


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--case-file", required=True)
    parser.add_argument("--pipeline-version")
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parents[2]
    ctx = RunContext.from_run_id(repo_root=repo_root, run_id=args.run_id)

    log_path = ctx.logs_dir / "pipeline.log"
    log_line(log_path, f"PIPELINE START run_id={ctx.run_id}")

    case_input = read_case_input(
        args.case_file, pipeline_version_override=args.pipeline_version, log_path=log_path
    )
    case_input["run_id"] = ctx.run_id
    case_file_path = Path(args.case_file)
    log_line(log_path, f"Loaded case_file run_id={ctx.run_id} file={case_file_path.name}")

    # --- Step: AG-00 ---
    step_id = "AG-00"
    step_dir = ctx.steps_dir / step_id
    step_dir.mkdir(parents=True, exist_ok=True)

    agent = AgentAG00IntakeNormalization()
    log_line(log_path, "Running AG-00 agent")

    agent_result = agent.run(case_input=case_input)
    output_path = step_dir / "output.json"

    if not agent_result.ok:
        write_json(step_dir / "agent_error.json", agent_result.output)
        log_line(log_path, "AG-00 agent self-validation FAILED")
        raise SystemExit(2)

    write_json(output_path, agent_result.output)
    log_line(log_path, f"AG-00 output written run_id={ctx.run_id}")

    # --- Gatekeeper validation ---
    step_contracts = load_step_contracts(str(repo_root / "configs/pipeline/step_contracts.yml"))
    contract = step_contracts[step_id]

    vr = validate_ag00_output(agent_result.output, contract)
    validator_payload = build_validator_payload(
        validation_result=vr,
        output_payload=agent_result.output,
        log_path=log_path,
    )

    write_json(step_dir / "validator.json", validator_payload)
    log_line(log_path, f"AG-00 gatekeeper ok={vr.ok}")

    if not vr.ok:
        log_line(log_path, "PIPELINE STOP (contract validation failed)")
        _log_skipped_steps(log_path, "AG-00")
        raise SystemExit(3)

    # Write meta artifact for downstream steps
    write_json(ctx.meta_dir / "case_normalized.json", agent_result.output["case_normalized"])
    write_json(ctx.meta_dir / "target_entity_stub.json", agent_result.output["target_entity_stub"])

     # --- Step: AG-01 ---
    step_id = "AG-01"
    step_dir = ctx.steps_dir / step_id
    step_dir.mkdir(parents=True, exist_ok=True)

    agent01 = AgentAG01SourceRegistry()
    log_line(log_path, "Running AG-01 agent")

    case_normalized = agent_result.output["case_normalized"]
    target_stub = agent_result.output["target_entity_stub"]

    agent01_result = agent01.run(
        case_input=case_input,
        meta_case_normalized=case_normalized,
        meta_target_entity_stub=target_stub,
    )

    if not agent01_result.ok:
        write_json(step_dir / "agent_error.json", agent01_result.output)
        log_line(log_path, "AG-01 agent self-validation FAILED")
        raise SystemExit(2)

    output_path = step_dir / "output.json"
    write_json(output_path, agent01_result.output)
    log_line(log_path, f"AG-01 output written run_id={ctx.run_id}")

    contract01 = step_contracts[step_id]
    vr01 = validate_ag01_output(agent01_result.output, contract01)

    validator_payload01 = build_validator_payload(
        validation_result=vr01,
        output_payload=agent01_result.output,
        log_path=log_path,
    )

    write_json(step_dir / "validator.json", validator_payload01)
    log_line(log_path, f"AG-01 gatekeeper ok={vr01.ok}")

    if not vr01.ok:
        log_line(log_path, "PIPELINE STOP (AG-01 contract validation failed)")
        _log_skipped_steps(log_path, "AG-01")
        raise SystemExit(3)

    # --- Step: AG-10 ---
    step_id = "AG-10"
    step_dir = ctx.steps_dir / step_id
    step_dir.mkdir(parents=True, exist_ok=True)

    agent10 = AgentAG10IdentityLegal()
    log_line(log_path, "Running AG-10 agent")

    case_normalized = agent_result.output["case_normalized"]
    target_stub = agent_result.output["target_entity_stub"]

    agent10_result = agent10.run(
        case_input=case_input,
        meta_case_normalized=case_normalized,
        meta_target_entity_stub=target_stub,
    )

    if not agent10_result.ok:
        write_json(step_dir / "agent_error.json", agent10_result.output)
        log_line(log_path, "AG-10 agent self-validation FAILED")
        raise SystemExit(2)

    output_path = step_dir / "output.json"
    write_json(output_path, agent10_result.output)
    log_line(log_path, f"AG-10 output written run_id={ctx.run_id}")

    contract10 = step_contracts[step_id]
    vr10 = validate_ag10_output(
        agent10_result.output,
        contract10,
        expected_entity_key=str(case_normalized.get("entity_key", "")),
        expected_domain=str(case_normalized.get("web_domain_normalized", "")),
    )

    validator_payload10 = build_validator_payload(
        validation_result=vr10,
        output_payload=agent10_result.output,
        log_path=log_path,
    )

    write_json(step_dir / "validator.json", validator_payload10)
    log_line(log_path, f"AG-10 gatekeeper ok={vr10.ok}")

    if not vr10.ok:
        log_line(log_path, "PIPELINE STOP (AG-10 contract validation failed)")
        _log_skipped_steps(log_path, "AG-10")
        raise SystemExit(3)

    # --- Step: AG-11 ---
    step_id = "AG-11"
    step_dir = ctx.steps_dir / step_id
    step_dir.mkdir(parents=True, exist_ok=True)

    agent11 = AgentAG11LocationsSites()
    log_line(log_path, "Running AG-11 agent")

    case_normalized = agent_result.output["case_normalized"]
    target_stub = agent_result.output["target_entity_stub"]

    agent11_result = agent11.run(
        case_input=case_input,
        meta_case_normalized=case_normalized,
        meta_target_entity_stub=target_stub,
    )

    if not agent11_result.ok:
        write_json(step_dir / "agent_error.json", agent11_result.output)
        log_line(log_path, "AG-11 agent self-validation FAILED")
        raise SystemExit(2)

    output_path = step_dir / "output.json"
    write_json(output_path, agent11_result.output)
    log_line(log_path, f"AG-11 output written run_id={ctx.run_id}")

    contract11 = step_contracts[step_id]
    vr11 = validate_ag11_output(agent11_result.output, contract11)

    validator_payload11 = build_validator_payload(
        validation_result=vr11,
        output_payload=agent11_result.output,
        log_path=log_path,
    )

    write_json(step_dir / "validator.json", validator_payload11)
    log_line(log_path, f"AG-11 gatekeeper ok={vr11.ok}")

    if not vr11.ok:
        log_line(log_path, "PIPELINE STOP (AG-11 contract validation failed)")
        _log_skipped_steps(log_path, "AG-11")
        raise SystemExit(3)

    # --- Step: AG-20 ---
    step_id = "AG-20"
    step_dir = ctx.steps_dir / step_id
    step_dir.mkdir(parents=True, exist_ok=True)

    agent20 = AgentAG20CompanySize()
    log_line(log_path, "Running AG-20 agent")

    case_normalized = agent_result.output["case_normalized"]
    target_stub = agent_result.output["target_entity_stub"]

    agent20_result = agent20.run(
        case_input=case_input,
        meta_case_normalized=case_normalized,
        meta_target_entity_stub=target_stub,
    )

    if not agent20_result.ok:
        write_json(step_dir / "agent_error.json", agent20_result.output)
        log_line(log_path, "AG-20 agent self-validation FAILED")
        raise SystemExit(2)

    output_path = step_dir / "output.json"
    write_json(output_path, agent20_result.output)
    log_line(log_path, f"AG-20 output written run_id={ctx.run_id}")

    contract20 = step_contracts[step_id]
    vr20 = validate_ag20_output(
        agent20_result.output,
        contract20,
        expected_entity_key=str(case_normalized.get("entity_key", "")),
        expected_domain=str(case_normalized.get("web_domain_normalized", "")),
    )

    validator_payload20 = build_validator_payload(
        validation_result=vr20,
        output_payload=agent20_result.output,
        log_path=log_path,
    )

    write_json(step_dir / "validator.json", validator_payload20)
    log_line(log_path, f"AG-20 gatekeeper ok={vr20.ok}")

    if not vr20.ok:
        log_line(log_path, "PIPELINE STOP (AG-20 contract validation failed)")
        _log_skipped_steps(log_path, "AG-20")
        raise SystemExit(3)

    # --- Step: AG-21 ---
    step_id = "AG-21"
    step_dir = ctx.steps_dir / step_id
    step_dir.mkdir(parents=True, exist_ok=True)

    agent21 = AgentAG21FinancialSignals()
    log_line(log_path, "Running AG-21 agent")

    agent21_result = agent21.run(case_input=case_input)

    if not agent21_result.ok:
        write_json(step_dir / "agent_error.json", agent21_result.output)
        log_line(log_path, "AG-21 agent self-validation FAILED")
        raise SystemExit(2)

    output_path = step_dir / "output.json"
    write_json(output_path, agent21_result.output)
    log_line(log_path, f"AG-21 output written run_id={ctx.run_id}")

    contract21 = step_contracts[step_id]
    vr21 = validate_research_output(agent21_result.output, contract21)

    validator_payload21 = build_validator_payload(
        validation_result=vr21,
        output_payload=agent21_result.output,
        log_path=log_path,
    )

    write_json(step_dir / "validator.json", validator_payload21)
    log_line(log_path, f"AG-21 gatekeeper ok={vr21.ok}")

    if not vr21.ok:
        log_line(log_path, "PIPELINE STOP (AG-21 contract validation failed)")
        _log_skipped_steps(log_path, "AG-21")
        raise SystemExit(3)

    # --- Step: AG-30 ---
    step_id = "AG-30"
    step_dir = ctx.steps_dir / step_id
    step_dir.mkdir(parents=True, exist_ok=True)

    agent30 = AgentAG30Portfolio()
    log_line(log_path, "Running AG-30 agent")

    agent30_result = agent30.run(case_input=case_input)

    if not agent30_result.ok:
        write_json(step_dir / "agent_error.json", agent30_result.output)
        log_line(log_path, "AG-30 agent self-validation FAILED")
        raise SystemExit(2)

    output_path = step_dir / "output.json"
    write_json(output_path, agent30_result.output)
    log_line(log_path, f"AG-30 output written run_id={ctx.run_id}")

    contract30 = step_contracts[step_id]
    vr30 = validate_research_output(agent30_result.output, contract30)

    validator_payload30 = build_validator_payload(
        validation_result=vr30,
        output_payload=agent30_result.output,
        log_path=log_path,
    )

    write_json(step_dir / "validator.json", validator_payload30)
    log_line(log_path, f"AG-30 gatekeeper ok={vr30.ok}")

    if not vr30.ok:
        log_line(log_path, "PIPELINE STOP (AG-30 contract validation failed)")
        _log_skipped_steps(log_path, "AG-30")
        raise SystemExit(3)

    # --- Step: AG-31 ---
    step_id = "AG-31"
    step_dir = ctx.steps_dir / step_id
    step_dir.mkdir(parents=True, exist_ok=True)

    agent31 = AgentAG31MarketsFocus()
    log_line(log_path, "Running AG-31 agent")

    agent31_result = agent31.run(case_input=case_input)

    if not agent31_result.ok:
        write_json(step_dir / "agent_error.json", agent31_result.output)
        log_line(log_path, "AG-31 agent self-validation FAILED")
        raise SystemExit(2)

    output_path = step_dir / "output.json"
    write_json(output_path, agent31_result.output)
    log_line(log_path, f"AG-31 output written run_id={ctx.run_id}")

    contract31 = step_contracts[step_id]
    vr31 = validate_research_output(agent31_result.output, contract31)

    validator_payload31 = build_validator_payload(
        validation_result=vr31,
        output_payload=agent31_result.output,
        log_path=log_path,
    )

    write_json(step_dir / "validator.json", validator_payload31)
    log_line(log_path, f"AG-31 gatekeeper ok={vr31.ok}")

    if not vr31.ok:
        log_line(log_path, "PIPELINE STOP (AG-31 contract validation failed)")
        _log_skipped_steps(log_path, "AG-31")
        raise SystemExit(3)

    # --- Step: AG-40 ---
    step_id = "AG-40"
    step_dir = ctx.steps_dir / step_id
    step_dir.mkdir(parents=True, exist_ok=True)

    agent40 = AgentAG40TargetCustomers()
    log_line(log_path, "Running AG-40 agent")

    agent40_result = agent40.run(case_input=case_input)

    if not agent40_result.ok:
        write_json(step_dir / "agent_error.json", agent40_result.output)
        log_line(log_path, "AG-40 agent self-validation FAILED")
        raise SystemExit(2)

    output_path = step_dir / "output.json"
    write_json(output_path, agent40_result.output)
    log_line(log_path, f"AG-40 output written run_id={ctx.run_id}")

    contract40 = step_contracts[step_id]
    vr40 = validate_research_output(agent40_result.output, contract40)

    validator_payload40 = build_validator_payload(
        validation_result=vr40,
        output_payload=agent40_result.output,
        log_path=log_path,
    )

    write_json(step_dir / "validator.json", validator_payload40)
    log_line(log_path, f"AG-40 gatekeeper ok={vr40.ok}")

    if not vr40.ok:
        log_line(log_path, "PIPELINE STOP (AG-40 contract validation failed)")
        _log_skipped_steps(log_path, "AG-40")
        raise SystemExit(3)

    # --- Step: AG-41 ---
    step_id = "AG-41"
    step_dir = ctx.steps_dir / step_id
    step_dir.mkdir(parents=True, exist_ok=True)

    agent41 = AgentAG41PeerDiscovery()
    log_line(log_path, "Running AG-41 agent")

    agent41_result = agent41.run(case_input=case_input)

    if not agent41_result.ok:
        write_json(step_dir / "agent_error.json", agent41_result.output)
        log_line(log_path, "AG-41 agent self-validation FAILED")
        raise SystemExit(2)

    output_path = step_dir / "output.json"
    write_json(output_path, agent41_result.output)
    log_line(log_path, f"AG-41 output written run_id={ctx.run_id}")

    contract41 = step_contracts[step_id]
    vr41 = validate_research_output(agent41_result.output, contract41)

    validator_payload41 = build_validator_payload(
        validation_result=vr41,
        output_payload=agent41_result.output,
        log_path=log_path,
    )

    write_json(step_dir / "validator.json", validator_payload41)
    log_line(log_path, f"AG-41 gatekeeper ok={vr41.ok}")

    if not vr41.ok:
        log_line(log_path, "PIPELINE STOP (AG-41 contract validation failed)")
        _log_skipped_steps(log_path, "AG-41")
        raise SystemExit(3)

    # --- Step: AG-42 ---
    step_id = "AG-42"
    step_dir = ctx.steps_dir / step_id
    step_dir.mkdir(parents=True, exist_ok=True)

    agent42 = AgentAG42CustomersOfManufacturers()
    log_line(log_path, "Running AG-42 agent")

    agent42_result = agent42.run(case_input=case_input)

    if not agent42_result.ok:
        write_json(step_dir / "agent_error.json", agent42_result.output)
        log_line(log_path, "AG-42 agent self-validation FAILED")
        raise SystemExit(2)

    output_path = step_dir / "output.json"
    write_json(output_path, agent42_result.output)
    log_line(log_path, f"AG-42 output written run_id={ctx.run_id}")

    contract42 = step_contracts[step_id]
    vr42 = validate_research_output(agent42_result.output, contract42)

    validator_payload42 = build_validator_payload(
        validation_result=vr42,
        output_payload=agent42_result.output,
        log_path=log_path,
    )

    write_json(step_dir / "validator.json", validator_payload42)
    log_line(log_path, f"AG-42 gatekeeper ok={vr42.ok}")

    if not vr42.ok:
        log_line(log_path, "PIPELINE STOP (AG-42 contract validation failed)")
        _log_skipped_steps(log_path, "AG-42")
        raise SystemExit(3)

    # --- Step: AG-70 ---
    step_id = "AG-70"
    step_dir = ctx.steps_dir / step_id
    step_dir.mkdir(parents=True, exist_ok=True)

    agent70 = AgentAG70SupplyChainTech()
    log_line(log_path, "Running AG-70 agent")

    agent70_result = agent70.run(case_input=case_input)

    if not agent70_result.ok:
        write_json(step_dir / "agent_error.json", agent70_result.output)
        log_line(log_path, "AG-70 agent self-validation FAILED")
        raise SystemExit(2)

    output_path = step_dir / "output.json"
    write_json(output_path, agent70_result.output)
    log_line(log_path, f"AG-70 output written run_id={ctx.run_id}")

    contract70 = step_contracts[step_id]
    vr70 = validate_research_output(agent70_result.output, contract70)

    validator_payload70 = build_validator_payload(
        validation_result=vr70,
        output_payload=agent70_result.output,
        log_path=log_path,
    )

    write_json(step_dir / "validator.json", validator_payload70)
    log_line(log_path, f"AG-70 gatekeeper ok={vr70.ok}")

    if not vr70.ok:
        log_line(log_path, "PIPELINE STOP (AG-70 contract validation failed)")
        _log_skipped_steps(log_path, "AG-70")
        raise SystemExit(3)

    # --- Step: AG-71 ---
    step_id = "AG-71"
    step_dir = ctx.steps_dir / step_id
    step_dir.mkdir(parents=True, exist_ok=True)

    agent71 = AgentAG71SupplyChainRisks()
    log_line(log_path, "Running AG-71 agent")

    agent71_result = agent71.run(case_input=case_input)

    if not agent71_result.ok:
        write_json(step_dir / "agent_error.json", agent71_result.output)
        log_line(log_path, "AG-71 agent self-validation FAILED")
        raise SystemExit(2)

    output_path = step_dir / "output.json"
    write_json(output_path, agent71_result.output)
    log_line(log_path, f"AG-71 output written run_id={ctx.run_id}")

    contract71 = step_contracts[step_id]
    vr71 = validate_research_output(agent71_result.output, contract71)

    validator_payload71 = build_validator_payload(
        validation_result=vr71,
        output_payload=agent71_result.output,
        log_path=log_path,
    )

    write_json(step_dir / "validator.json", validator_payload71)
    log_line(log_path, f"AG-71 gatekeeper ok={vr71.ok}")

    if not vr71.ok:
        log_line(log_path, "PIPELINE STOP (AG-71 contract validation failed)")
        _log_skipped_steps(log_path, "AG-71")
        raise SystemExit(3)

    # --- Step: AG-72 ---
    step_id = "AG-72"
    step_dir = ctx.steps_dir / step_id
    step_dir.mkdir(parents=True, exist_ok=True)

    agent72 = AgentAG72SustainabilityCircular()
    log_line(log_path, "Running AG-72 agent")

    agent72_result = agent72.run(case_input=case_input)

    if not agent72_result.ok:
        write_json(step_dir / "agent_error.json", agent72_result.output)
        log_line(log_path, "AG-72 agent self-validation FAILED")
        raise SystemExit(2)

    output_path = step_dir / "output.json"
    write_json(output_path, agent72_result.output)
    log_line(log_path, f"AG-72 output written run_id={ctx.run_id}")

    contract72 = step_contracts[step_id]
    vr72 = validate_research_output(agent72_result.output, contract72)

    validator_payload72 = build_validator_payload(
        validation_result=vr72,
        output_payload=agent72_result.output,
        log_path=log_path,
    )

    write_json(step_dir / "validator.json", validator_payload72)
    log_line(log_path, f"AG-72 gatekeeper ok={vr72.ok}")

    if not vr72.ok:
        log_line(log_path, "PIPELINE STOP (AG-72 contract validation failed)")
        _log_skipped_steps(log_path, "AG-72")
        raise SystemExit(3)

    # --- Step: AG-81 ---
    step_id = "AG-81"
    step_dir = ctx.steps_dir / step_id
    step_dir.mkdir(parents=True, exist_ok=True)

    agent81 = AgentAG81IndustryTrends()
    log_line(log_path, "Running AG-81 agent")

    agent81_result = agent81.run(case_input=case_input)

    if not agent81_result.ok:
        write_json(step_dir / "agent_error.json", agent81_result.output)
        log_line(log_path, "AG-81 agent self-validation FAILED")
        raise SystemExit(2)

    output_path = step_dir / "output.json"
    write_json(output_path, agent81_result.output)
    log_line(log_path, f"AG-81 output written run_id={ctx.run_id}")

    contract81 = step_contracts[step_id]
    vr81 = validate_research_output(agent81_result.output, contract81)

    validator_payload81 = build_validator_payload(
        validation_result=vr81,
        output_payload=agent81_result.output,
        log_path=log_path,
    )

    write_json(step_dir / "validator.json", validator_payload81)
    log_line(log_path, f"AG-81 gatekeeper ok={vr81.ok}")

    if not vr81.ok:
        log_line(log_path, "PIPELINE STOP (AG-81 contract validation failed)")
        _log_skipped_steps(log_path, "AG-81")
        raise SystemExit(3)

    # --- Step: AG-82 ---
    step_id = "AG-82"
    step_dir = ctx.steps_dir / step_id
    step_dir.mkdir(parents=True, exist_ok=True)

    agent82 = AgentAG82TradeFairsEvents()
    log_line(log_path, "Running AG-82 agent")

    agent82_result = agent82.run(case_input=case_input)

    if not agent82_result.ok:
        write_json(step_dir / "agent_error.json", agent82_result.output)
        log_line(log_path, "AG-82 agent self-validation FAILED")
        raise SystemExit(2)

    output_path = step_dir / "output.json"
    write_json(output_path, agent82_result.output)
    log_line(log_path, f"AG-82 output written run_id={ctx.run_id}")

    contract82 = step_contracts[step_id]
    vr82 = validate_research_output(agent82_result.output, contract82)

    validator_payload82 = build_validator_payload(
        validation_result=vr82,
        output_payload=agent82_result.output,
        log_path=log_path,
    )

    write_json(step_dir / "validator.json", validator_payload82)
    log_line(log_path, f"AG-82 gatekeeper ok={vr82.ok}")

    if not vr82.ok:
        log_line(log_path, "PIPELINE STOP (AG-82 contract validation failed)")
        _log_skipped_steps(log_path, "AG-82")
        raise SystemExit(3)

    # --- Step: AG-83 ---
    step_id = "AG-83"
    step_dir = ctx.steps_dir / step_id
    step_dir.mkdir(parents=True, exist_ok=True)

    agent83 = AgentAG83AssociationsMemberships()
    log_line(log_path, "Running AG-83 agent")

    agent83_result = agent83.run(case_input=case_input)

    if not agent83_result.ok:
        write_json(step_dir / "agent_error.json", agent83_result.output)
        log_line(log_path, "AG-83 agent self-validation FAILED")
        raise SystemExit(2)

    output_path = step_dir / "output.json"
    write_json(output_path, agent83_result.output)
    log_line(log_path, f"AG-83 output written run_id={ctx.run_id}")

    contract83 = step_contracts[step_id]
    vr83 = validate_research_output(agent83_result.output, contract83)

    validator_payload83 = build_validator_payload(
        validation_result=vr83,
        output_payload=agent83_result.output,
        log_path=log_path,
    )

    write_json(step_dir / "validator.json", validator_payload83)
    log_line(log_path, f"AG-83 gatekeeper ok={vr83.ok}")

    if not vr83.ok:
        log_line(log_path, "PIPELINE STOP (AG-83 contract validation failed)")
        _log_skipped_steps(log_path, "AG-83")
        raise SystemExit(3)

    # --- Step: AG-90 ---
    step_id = "AG-90"
    step_dir = ctx.steps_dir / step_id
    step_dir.mkdir(parents=True, exist_ok=True)

    agent90 = AgentAG90SalesPlaybook()
    log_line(log_path, "Running AG-90 agent")

    agent90_result = agent90.run(case_input=case_input)

    if not agent90_result.ok:
        write_json(step_dir / "agent_error.json", agent90_result.output)
        log_line(log_path, "AG-90 agent self-validation FAILED")
        raise SystemExit(2)

    output_path = step_dir / "output.json"
    write_json(output_path, agent90_result.output)
    log_line(log_path, f"AG-90 output written run_id={ctx.run_id}")

    contract90 = step_contracts[step_id]
    vr90 = validate_research_output(agent90_result.output, contract90)

    validator_payload90 = build_validator_payload(
        validation_result=vr90,
        output_payload=agent90_result.output,
        log_path=log_path,
    )

    write_json(step_dir / "validator.json", validator_payload90)
    log_line(log_path, f"AG-90 gatekeeper ok={vr90.ok}")

    if not vr90.ok:
        log_line(log_path, "PIPELINE STOP (AG-90 contract validation failed)")
        _log_skipped_steps(log_path, "AG-90")
        raise SystemExit(3)

    log_line(
        log_path,
        "PIPELINE END (AG-00, AG-01, AG-10, AG-11, AG-20, AG-21, AG-30, AG-31, "
        "AG-40, AG-41, AG-42, AG-70, AG-71, AG-72, AG-81, AG-82, AG-83, AG-90 completed successfully)",
    )

    report = build_report(ctx)
    report_path = ctx.exports_dir / "report.md"
    report_path.write_text(report, encoding="utf-8")
    relative_report_path = report_path.relative_to(ctx.run_root)
    log_line(log_path, f"Report written path={relative_report_path.as_posix()}")


if __name__ == "__main__":
    main()
