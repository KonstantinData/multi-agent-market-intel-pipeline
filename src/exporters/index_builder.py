from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Dict, List

from src.registry.entity_registry import Entity, EntityRegistry


@dataclass(frozen=True)
class IndexEntry:
    entity_id: str
    label: str
    entity_type: str
    domain: str | None


def _build_entry(entity: Entity | Dict[str, Any]) -> IndexEntry:
    if isinstance(entity, Entity):
        return IndexEntry(
            entity_id=entity.entity_id,
            label=entity.entity_name,
            entity_type=entity.entity_type,
            domain=entity.domain,
        )
    return IndexEntry(
        entity_id=str(entity.get("entity_id", "")),
        label=str(entity.get("entity_name", "")),
        entity_type=str(entity.get("entity_type", "")),
        domain=entity.get("domain"),
    )


def build_index(registry: EntityRegistry | Dict[str, Any]) -> List[Dict[str, Any]]:
    """Builds a deterministic index for navigation or UI search."""
    if isinstance(registry, EntityRegistry):
        entities = registry.entities_by_id.values()
    else:
        entities = registry.get("entities", []) if isinstance(registry, dict) else []

    entries = [_build_entry(entity) for entity in entities]
    entries.sort(key=lambda entry: (entry.entity_type, entry.label.lower()))
    return [asdict(entry) for entry in entries]
