from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Dict, Iterable, List

from src.registry.entity_registry import EntityRegistry, Relation


@dataclass(frozen=True)
class CrossrefRow:
    source_id: str
    relation_type: str
    target_id: str


def _rows_from_relations(relations: Iterable[Relation | Dict[str, str]]) -> List[CrossrefRow]:
    rows = []
    for rel in relations:
        if isinstance(rel, Relation):
            rows.append(
                CrossrefRow(
                    source_id=rel.source_id,
                    relation_type=rel.relation_type,
                    target_id=rel.target_id,
                )
            )
        else:
            rows.append(
                CrossrefRow(
                    source_id=str(rel.get("source_id", "")),
                    relation_type=str(rel.get("relation_type", "")),
                    target_id=str(rel.get("target_id", "")),
                )
            )
    return rows


def export_crossref_matrix(
    registry: EntityRegistry | Dict[str, list],
    output_path: Path,
) -> List[Dict[str, str]]:
    """Exports a simple cross-reference matrix as JSON."""
    if isinstance(registry, EntityRegistry):
        relations = registry.relations
    else:
        relations = registry.get("relations", []) if isinstance(registry, dict) else []

    rows = _rows_from_relations(relations)
    payload = [asdict(row) for row in rows]
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return payload
