from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict

from src.agents.ag00_intake_normalization.agent import AgentAG00IntakeNormalization
from src.orchestrator.logger import log_line
from src.orchestrator.run_context import RunContext
from src.validator.contract_validator import (
    load_step_contracts,
    validate_ag00_output,
)


def read_case_input(case_file: str) -> Dict[str, Any]:
    p = Path(case_file)
    return json.loads(p.read_text(encoding="utf-8"))


def write_json(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--case-file", required=True)
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parents[2]
    ctx = RunContext.from_run_id(repo_root=repo_root, run_id=args.run_id)

    log_path = ctx.logs_dir / "pipeline.log"
    log_line(log_path, f"PIPELINE START run_id={ctx.run_id}")

    case_input = read_case_input(args.case_file)
    log_line(log_path, f"Loaded case_file={args.case_file}")

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
    log_line(log_path, f"AG-00 output written: {output_path}")

    # --- Gatekeeper validation ---
    step_contracts = load_step_contracts(str(repo_root / "configs/pipeline/step_contracts.yml"))
    contract = step_contracts[step_id]

    vr = validate_ag00_output(agent_result.output, contract)
    validator_payload = {
        "step_id": vr.step_id,
        "ok": vr.ok,
        "errors": [
            {"code": e.code, "message": e.message, "path": e.path}
            for e in vr.errors
        ],
    }

    write_json(step_dir / "validator.json", validator_payload)
    log_line(log_path, f"AG-00 gatekeeper ok={vr.ok}")

    if not vr.ok:
        log_line(log_path, "PIPELINE STOP (contract validation failed)")
        raise SystemExit(3)

    # Write meta artifact for downstream steps
    write_json(ctx.meta_dir / "case_normalized.json", agent_result.output["case_normalized"])
    write_json(ctx.meta_dir / "target_entity_stub.json", agent_result.output["target_entity_stub"])

    log_line(log_path, "PIPELINE END (AG-00 completed successfully)")


if __name__ == "__main__":
    main()
