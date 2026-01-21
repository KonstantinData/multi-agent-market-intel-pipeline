from __future__ import annotations

from src.registry.entity_registry import Entity, EntityRegistry
from src.registry.merger import merge_registry


def test_merge_registry_updates_existing_and_adds_new_entities() -> None:
    registry = EntityRegistry()
    registry.add_entity(
        Entity(
            entity_id="TGT-001",
            entity_type="target_company",
            entity_name="Example Corp",
            domain="example.com",
            entity_key="domain:example.com",
            attributes={"employee_range": "n/v"},
            sources=[{"publisher": "seed", "url": "https://example.com"}],
        )
    )

    entities_delta = [
        {
            "entity_key": "domain:example.com",
            "entity_type": "target_company",
            "entity_name": "Example Corp",
            "domain": "example.com",
            "attributes": {"revenue_band": "n/v"},
            "sources": [{"publisher": "update", "url": "https://example.com"}],
        },
        {
            "entity_key": "domain:beta.example",
            "entity_type": "manufacturer",
            "entity_name": "Beta Works",
            "domain": "beta.example",
        },
        {
            "entity_key": "domain:beta.example",
            "entity_type": "manufacturer",
            "entity_name": "Beta Works Duplicate",
            "domain": "beta.example",
        },
    ]

    relations_delta = [
        {
            "source_id": "TGT-001",
            "relation_type": "peer_of",
            "target_id": "MFR-001",
        }
    ]

    report = merge_registry(
        registry=registry,
        entities_delta=entities_delta,
        relations_delta=relations_delta,
    )

    assert report.new_entities == 1
    assert report.updated_entities == 1
    assert report.new_relations == 1

    updated = registry.get_by_key("domain:example.com")
    assert updated is not None
    assert updated.attributes["employee_range"] == "n/v"
    assert updated.attributes["revenue_band"] == "n/v"
    assert {source["publisher"] for source in updated.sources} == {"seed", "update"}

    assert "MFR-001" in registry.entities_by_id
    assert len(registry.relations) == 1
