from __future__ import annotations

from typing import Dict, List

from src.registry.entity_registry import Relation


def build_crossref_graph(relations: List[Relation]) -> Dict[str, List[Dict[str, str]]]:
    """Builds a simple adjacency list for entity cross-references."""
    graph: Dict[str, List[Dict[str, str]]] = {}
    for relation in relations:
        graph.setdefault(relation.source_id, []).append(
            {
                "relation_type": relation.relation_type,
                "target_id": relation.target_id,
            }
        )
    return graph
