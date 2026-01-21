from __future__ import annotations

from src.registry.entity_registry import Entity, EntityRegistry
from src.registry.id_allocator import IdAllocator


def _registry_with_entities() -> EntityRegistry:
    registry = EntityRegistry()
    registry.add_entity(
        Entity(
            entity_id="MFR-005",
            entity_type="manufacturer",
            entity_name="Maker Co",
            domain="maker.example",
            entity_key="domain:maker.example",
        )
    )
    registry.add_entity(
        Entity(
            entity_id="CUS-010",
            entity_type="customer",
            entity_name="Buyer Co",
            domain="buyer.example",
            entity_key="domain:buyer.example",
        )
    )
    return registry


def test_id_allocator_seeds_and_allocates_incrementally() -> None:
    registry = _registry_with_entities()
    allocator = IdAllocator()

    assert allocator.allocate("target_company", registry) == "TGT-001"
    assert allocator.allocate("manufacturer", registry) == "MFR-006"
    assert allocator.allocate("customer", registry) == "CUS-011"
    assert allocator.allocate("unknown_type", registry) == "ENT-001"
