from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List

from src.registry.deduper import dedupe_entities
from src.registry.entity_registry import Entity, EntityRegistry, Relation
from src.registry.id_allocator import IdAllocator


@dataclass(frozen=True)
class MergeReport:
    new_entities: int
    updated_entities: int
    new_relations: int


def merge_registry(
    *,
    registry: EntityRegistry,
    entities_delta: List[Dict[str, Any]],
    relations_delta: List[Dict[str, Any]],
    allocator: IdAllocator | None = None,
) -> MergeReport:
    """Merge agent deltas into the central registry."""
    allocator = allocator or IdAllocator()

    deduped_entities = dedupe_entities(entities_delta)
    new_entities = 0
    updated_entities = 0

    for entity_payload in deduped_entities:
        entity_key = str(entity_payload.get("entity_key", ""))
        existing = registry.get_by_key(entity_key) if entity_key else None

        if existing is None:
            entity_id = entity_payload.get("entity_id")
            if not entity_id:
                entity_id = allocator.allocate(
                    str(entity_payload.get("entity_type", "entity")), registry
                )
            entity_payload["entity_id"] = entity_id
            entity = Entity.from_dict(entity_payload)
            registry.add_entity(entity)
            new_entities += 1
        else:
            existing.attributes.update(entity_payload.get("attributes", {}))
            existing.sources.extend(entity_payload.get("sources", []))
            updated_entities += 1

    new_relations = 0
    for relation_payload in relations_delta:
        relation = Relation.from_dict(relation_payload)
        registry.add_relation(relation)
        new_relations += 1

    return MergeReport(
        new_entities=new_entities,
        updated_entities=updated_entities,
        new_relations=new_relations,
    )
