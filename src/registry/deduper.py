from __future__ import annotations

from typing import Any, Dict, List, Set

from src.registry.entity_key import build_entity_key, normalize_domain


def dedupe_entities(entities: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Deduplicate entities using entity_key or domain/name heuristics."""
    seen: Set[str] = set()
    deduped: List[Dict[str, Any]] = []

    for entity in entities:
        entity_key = str(entity.get("entity_key") or "")
        if not entity_key or entity_key == "n/v":
            entity_key = build_entity_key(
                domain=entity.get("domain"),
                name=entity.get("entity_name"),
            )
        domain = normalize_domain(str(entity.get("domain") or ""))
        dedupe_key = entity_key if entity_key != "n/v" else domain
        if not dedupe_key:
            dedupe_key = f"name:{str(entity.get('entity_name', '')).lower()}"

        if dedupe_key in seen:
            continue
        seen.add(dedupe_key)
        entity["entity_key"] = entity_key
        deduped.append(entity)

    return deduped
