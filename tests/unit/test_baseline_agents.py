"""
DESCRIPTION
-----------
Unit tests for baseline agents and registry behavior.
These tests ensure all planned steps are importable and contract-compliant.
"""


from __future__ import annotations

from typing import Dict, Any

import pytest

from src.orchestrator.step_registry import build_agent
from src.validator.step_validator import validate_step_output
from src.registry.entity_registry import EntityRegistry


@pytest.mark.parametrize(
    "step_id",
    [
        "AG-21", "AG-30", "AG-31", "AG-40", "AG-41", "AG-42",
        "AG-50", "AG-51", "AG-60", "AG-61", "AG-62",
        "AG-70", "AG-71", "AG-72",
        "AG-80", "AG-81", "AG-82", "AG-83", "AG-90",
    ],
)
def test_baseline_agent_structure(step_id: str) -> None:
    agent = build_agent(step_id)
    case_input: Dict[str, Any] = {
        "run_id": "RUN-UNIT",
        "company_name": "Example GmbH",
        "company_web_domain": "example.com",
    }

    result = agent.run(case_input, meta_case_normalized={}, meta_target_entity_stub={"entity_id": "TGT-001"})
    assert result.ok is True
    assert isinstance(result.output, dict)

    validation = validate_step_output(step_id=step_id, output=result.output)
    assert validation["ok"] is True


def test_entity_registry_deduplication() -> None:
    registry = EntityRegistry(id_policy={"key_fields": ["entity_type", "entity_name"], "prefix": "TEST"}, namespace="RUN-UNIT")

    registry.add_entities([
        {"entity_type": "peer_company", "entity_name": "ACME"},
        {"entity_type": "peer_company", "entity_name": "ACME"},
    ])

    snap = registry.snapshot()
    assert len(snap["entities"]) == 1
