from __future__ import annotations

from src.orchestrator.dag_loader import load_dag
from src.validator.contract_validator import load_step_contracts


_REQUIRED_STEP_META_FIELDS = {
    "step_id",
    "agent_name",
    "run_id",
    "started_at_utc",
    "finished_at_utc",
    "pipeline_version",
}


def test_step_contracts_cover_dag_and_required_fields() -> None:
    contracts = load_step_contracts("configs/pipeline/step_contracts.yml")
    dag = load_dag("configs/pipeline/dag.yml")

    step_ids = [node.step_id for node in dag.nodes]
    assert step_ids, "DAG should define pipeline steps"

    for step_id in step_ids:
        assert step_id in contracts, f"Missing contract for {step_id}"
        contract = contracts[step_id]
        assert contract["step_id"] == step_id
        assert contract.get("agent_name"), f"Missing agent_name for {step_id}"

        outputs = contract.get("outputs", {})
        required_sections = outputs.get("required_sections", [])
        assert "step_meta" in required_sections
        assert "findings" in required_sections

        step_meta_fields = set(outputs.get("step_meta_required_fields", []))
        assert _REQUIRED_STEP_META_FIELDS.issubset(step_meta_fields)

        validation = contract.get("validation", {})
        hard_fail_if = validation.get("hard_fail_if", [])
        assert hard_fail_if, f"Expected hard_fail_if rules for {step_id}"
