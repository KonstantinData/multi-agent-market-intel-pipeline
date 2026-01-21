from __future__ import annotations

from src.registry.entity_registry import Entity, EntityRegistry, Relation
from src.validator.crossref_validator import validate_crossrefs


def test_crossref_validator_detects_missing_entities() -> None:
    registry = EntityRegistry()
    registry.add_entity(
        Entity(
            entity_id="TGT-001",
            entity_type="target_company",
            entity_name="Example Corp",
            domain="example.com",
            entity_key="domain:example.com",
        )
    )

    relations = [
        Relation(
            source_id="TGT-001",
            relation_type="supplies_to",
            target_id="CUS-001",
        ),
        Relation(
            source_id="MFR-404",
            relation_type="peer_of",
            target_id="TGT-001",
        ),
    ]

    issues = validate_crossrefs(registry, relations)

    assert len(issues) == 2
    assert issues[0].path == "$.relations[0].target_id"
    assert "CUS-001" in issues[0].message
    assert issues[1].path == "$.relations[1].source_id"
    assert "MFR-404" in issues[1].message


def test_crossref_validator_accepts_valid_relations() -> None:
    registry = EntityRegistry()
    registry.add_entity(
        Entity(
            entity_id="TGT-001",
            entity_type="target_company",
            entity_name="Example Corp",
            domain="example.com",
            entity_key="domain:example.com",
        )
    )
    registry.add_entity(
        Entity(
            entity_id="CUS-001",
            entity_type="customer",
            entity_name="Customer One",
            domain=None,
            entity_key="name:customer one",
        )
    )

    relations = [
        Relation(
            source_id="TGT-001",
            relation_type="supplies_to",
            target_id="CUS-001",
        )
    ]

    issues = validate_crossrefs(registry, relations)

    assert issues == []
