from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterable, List

from src.registry.entity_registry import Entity, EntityRegistry


@dataclass(frozen=True)
class ExportedEntity:
    entity_id: str
    entity_type: str
    entity_name: str
    domain: str | None
    entity_key: str
    attributes: Dict[str, Any] = field(default_factory=dict)


def _coerce_entity(entity: Entity | Dict[str, Any]) -> ExportedEntity:
    if isinstance(entity, Entity):
        return ExportedEntity(
            entity_id=entity.entity_id,
            entity_type=entity.entity_type,
            entity_name=entity.entity_name,
            domain=entity.domain,
            entity_key=entity.entity_key,
            attributes=entity.attributes,
        )
    return ExportedEntity(
        entity_id=str(entity.get("entity_id", "")),
        entity_type=str(entity.get("entity_type", "")),
        entity_name=str(entity.get("entity_name", "")),
        domain=entity.get("domain"),
        entity_key=str(entity.get("entity_key", "")),
        attributes=dict(entity.get("attributes", {})),
    )


def _extract_entities(registry: EntityRegistry | Dict[str, Any]) -> Iterable[ExportedEntity]:
    if isinstance(registry, EntityRegistry):
        return [_coerce_entity(entity) for entity in registry.entities_by_id.values()]
    entities = registry.get("entities", []) if isinstance(registry, dict) else []
    return [_coerce_entity(entity) for entity in entities]


def export_entities(
    registry: EntityRegistry | Dict[str, Any],
    output_path: Path,
) -> List[Dict[str, Any]]:
    """Export entity registry into a machine-readable JSON list."""
    exported = [asdict(entity) for entity in _extract_entities(registry)]
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(exported, indent=2), encoding="utf-8")
    return exported
