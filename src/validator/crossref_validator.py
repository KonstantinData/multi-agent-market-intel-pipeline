from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, List, Set

from src.registry.entity_registry import EntityRegistry, Relation


@dataclass(frozen=True)
class CrossrefIssue:
    path: str
    message: str


def validate_crossrefs(
    registry: EntityRegistry,
    relations: Iterable[Relation],
    path_prefix: str = "$.relations",
) -> List[CrossrefIssue]:
    """Ensures relations reference existing registry entities."""
    issues: List[CrossrefIssue] = []
    valid_ids: Set[str] = set(registry.entities_by_id.keys())
    for idx, relation in enumerate(relations):
        if relation.source_id not in valid_ids:
            issues.append(
                CrossrefIssue(
                    path=f"{path_prefix}[{idx}].source_id",
                    message=f"Unknown source_id {relation.source_id}",
                )
            )
        if relation.target_id not in valid_ids:
            issues.append(
                CrossrefIssue(
                    path=f"{path_prefix}[{idx}].target_id",
                    message=f"Unknown target_id {relation.target_id}",
                )
            )
    return issues
