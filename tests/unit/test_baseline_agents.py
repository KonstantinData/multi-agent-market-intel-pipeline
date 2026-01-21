"""Unit tests for baseline agents and registry logic."""
from pathlib import Path

import pytest

from src.agents.common.baseline_agent import BaselineAgent
from src.registry.entity_registry import EntityRegistry


@pytest.mark.parametrize("step_id", [
    "AG-21", "AG-30", "AG-31", "AG-40", "AG-42", "AG-50", "AG-51",
    "AG-60", "AG-61", "AG-70", "AG-71", "AG-72", "AG-80", "AG-81", "AG-83", "AG-90"
])
def test_baseline_agent_structure(step_id):
    agent_cls = __import__(f"src.agents.{step_id.lower().replace('-', '')}.agent", fromlist=["Agent"])
    agent = agent_cls.Agent("RUN-TEST")  # type: ignore
    result = agent.execute(case_normalized={}, registry={})
    assert "step_meta" in result
    assert "entities_delta" in result
    assert "relations_delta" in result
    assert isinstance(result["entities_delta"], list)
    assert isinstance(result["relations_delta"], list)


def test_entity_registry_deduplication(tmp_path: Path):
    registry = EntityRegistry(run_meta_dir=tmp_path, id_policy={"key_fields": ["type", "name"], "prefix": "TEST"})
    entities = [
        {"type": "company", "name": "Acme Corp", "extra": "info1"},
        {"type": "company", "name": "Acme Corp", "extra": "info2"},
    ]
    registry.add_entities(entities)
    assert len(registry.entities) == 1
    ent = list(registry.entities.values())[0]
    assert ent["extra"] == "info2"