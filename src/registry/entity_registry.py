# PATH: src/registry/entity_registry.py
# ACTION: REPLACE

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from typing import Any, Dict, List


def _stable_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _canonical_json(obj: Any) -> str:
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _entity_dedup_key(entity: Dict[str, Any]) -> str:
    """
    Deterministic deduplication key.

    Priority:
    1) domain / website_domain
    2) url / website
    3) legal_name + legal_form
    4) full canonical json
    """
    domain = (entity.get("domain") or entity.get("website_domain") or "").strip().lower()
    url = (entity.get("url") or entity.get("website") or "").strip().lower()
    legal_name = (entity.get("legal_name") or entity.get("name") or "").strip().lower()
    legal_form = (entity.get("legal_form") or "").strip().lower()

    if domain:
        return f"domain:{domain}"
    if url:
        return f"url:{url}"
    if legal_name:
        return f"name:{legal_name}|form:{legal_form}"
    return f"raw:{_canonical_json(entity)}"


def _stable_entity_id(namespace: str, dedup_key: str) -> str:
    """
    Deterministic stable ID based on namespace + dedup_key.
    """
    return _stable_hash(f"{namespace}::{dedup_key}")[:16]


@dataclass
class EntityRegistry:
    """
    Deterministic entity registry used across steps.

    - stable IDs (hash-based)
    - deduplication by canonical key
    - deterministic export ordering
    """

    namespace: str = "default"
    entities_by_id: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    entity_id_by_dedup_key: Dict[str, str] = field(default_factory=dict)
    relations: List[Dict[str, Any]] = field(default_factory=list)

    def upsert_entity(self, entity: Dict[str, Any]) -> str:
        dedup_key = _entity_dedup_key(entity)
        entity_id = self.entity_id_by_dedup_key.get(dedup_key)

        if not entity_id:
            entity_id = _stable_entity_id(self.namespace, dedup_key)
            self.entity_id_by_dedup_key[dedup_key] = entity_id

        existing = self.entities_by_id.get(entity_id, {})
        merged = dict(existing)

        for k, v in (entity or {}).items():
            if v is None:
                continue
            if k not in merged:
                merged[k] = v
                continue
            if merged.get(k) in ("", "n/v") and v not in ("", "n/v"):
                merged[k] = v

        merged["entity_id"] = entity_id
        self.entities_by_id[entity_id] = merged
        return entity_id

    def add_entities(self, entities: List[Dict[str, Any]]) -> List[str]:
        ids: List[str] = []
        for e in entities or []:
            ids.append(self.upsert_entity(e))
        return ids

    def add_relations(self, relations: List[Dict[str, Any]]) -> None:
        for r in relations or []:
            self.relations.append(r)

    def ingest_step_output(self, step_id: str, step_output: Dict[str, Any]) -> None:
        """
        Ingest generic step output format.
        """
        self.add_entities(step_output.get("entities_delta") or [])
        self.add_relations(step_output.get("relations_delta") or [])

    def export_entities(self) -> List[Dict[str, Any]]:
        return [self.entities_by_id[k] for k in sorted(self.entities_by_id.keys())]

    def export_relations(self) -> List[Dict[str, Any]]:
        return sorted(self.relations, key=_canonical_json)

    def to_export_payload(self) -> Dict[str, Any]:
        return {
            "namespace": self.namespace,
            "entities": self.export_entities(),
            "relations": self.export_relations(),
        }


__all__ = ["EntityRegistry"]
