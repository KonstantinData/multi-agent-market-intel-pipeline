"""
DESCRIPTION
-----------
EntityRegistry is a deterministic, run-scoped state store that aggregates all entities,
relations, findings, and sources emitted by steps.

Key requirement:
- Anything discovered by any agent must be readable by all later agents.
This is implemented by persisting a registry snapshot after each step under
artifacts/runs/<run_id>/meta/entity_registry.json.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


#note: Deterministically serialize a dict into a canonical string for hashing and sorting.
def _canonical(obj: Any) -> str:
    if obj is None:
        return "null"
    if isinstance(obj, (str, int, float, bool)):
        return str(obj)
    if isinstance(obj, list):
        return "[" + ",".join(_canonical(x) for x in obj) + "]"
    if isinstance(obj, dict):
        items = sorted((str(k), _canonical(v)) for k, v in obj.items())
        return "{" + ",".join(f"{k}:{v}" for k, v in items) + "}"
    return str(obj)


#note: Stable sha256 helper for deterministic IDs.
def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


#note: Derive a deterministic entity_id when one is missing.
def _derive_entity_id(prefix: str, key: str) -> str:
    #note: IDs are short but collision-resistant enough for this pipeline.
    return f"{prefix}-{_sha256(key)[:12].upper()}"


@dataclass
class EntityRegistry:
    """
    #note: Aggregates all pipeline-delivered deltas into a deterministic, mergeable store.
    """

    id_policy: Dict[str, Any]
    namespace: str = "RUN"
    entities_by_id: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    relations: List[Dict[str, Any]] = field(default_factory=list)
    findings: List[Dict[str, Any]] = field(default_factory=list)
    sources: List[Dict[str, Any]] = field(default_factory=list)

    #note: Index for deduplication when step outputs omit entity_id.
    _id_by_dedup_key: Dict[str, str] = field(default_factory=dict)

    #note: Add or merge entities emitted by a step into the registry.
    def add_entities(self, entities: List[Dict[str, Any]]) -> None:
        key_fields: List[str] = list(self.id_policy.get("key_fields") or [])
        prefix: str = str(self.id_policy.get("prefix") or "ENT")

        for ent in entities or []:
            if not isinstance(ent, dict):
                continue

            explicit_id = str(ent.get("entity_id") or "").strip()
            ent_type = str(ent.get("entity_type") or ent.get("type") or "").strip()
            ent_name = str(ent.get("entity_name") or ent.get("name") or "").strip()

            #note: Build dedup key from configured fields if entity_id is missing.
            dedup_parts: List[str] = []
            for f in key_fields:
                val = ent.get(f)
                dedup_parts.append(str(val).strip())
            if not dedup_parts:
                dedup_parts = [ent_type, ent_name]

            dedup_key = _canonical(dedup_parts)

            entity_id = explicit_id
            if not entity_id:
                entity_id = self._id_by_dedup_key.get(dedup_key)
            if not entity_id:
                entity_id = _derive_entity_id(prefix, f"{self.namespace}:{dedup_key}")
                self._id_by_dedup_key[dedup_key] = entity_id

            existing = self.entities_by_id.get(entity_id, {})
            merged = dict(existing)

            #note: Merge rule: Agent data overwrites intake data except for domain.
            for k, v in ent.items():
                if v is None:
                    continue
                    
                # Never overwrite domain - preserve intake domain
                if k == "domain" and k in merged and merged[k] not in ("", "n/v", "N/V", None):
                    continue
                    
                # For other fields: agent data overwrites intake data if more complete
                if k not in merged or merged.get(k) in ("", "n/v", "N/V", None):
                    merged[k] = v
                else:
                    # Agent data is more complete than intake data - overwrite
                    if len(str(v).strip()) > len(str(merged.get(k, "")).strip()):
                        merged[k] = v

            merged["entity_id"] = entity_id
            if ent_type:
                merged.setdefault("entity_type", ent_type)
            # Update both entity_name and legal_name if one is provided
            if ent_name:
                if "legal_name" in ent and ent["legal_name"] not in ("", "n/v", "N/V", None):
                    merged["entity_name"] = ent["legal_name"]
                else:
                    merged.setdefault("entity_name", ent_name)

            self.entities_by_id[entity_id] = merged

    #note: Add relation deltas with deterministic sorting.
    def add_relations(self, relations: List[Dict[str, Any]]) -> None:
        for rel in relations or []:
            if isinstance(rel, dict):
                self.relations.append(rel)
        self.relations = sorted(self.relations, key=_canonical)

    #note: Add finding objects; we keep stable ordering.
    def add_findings(self, findings: List[Dict[str, Any]]) -> None:
        for f in findings or []:
            if isinstance(f, dict):
                self.findings.append(f)
        self.findings = sorted(self.findings, key=_canonical)

    #note: Add sources; keep stable order and remove duplicates by canonical string.
    def add_sources(self, sources: List[Dict[str, Any]]) -> None:
        seen = set(_canonical(s) for s in self.sources)
        for s in sources or []:
            if not isinstance(s, dict):
                continue
            key = _canonical(s)
            if key in seen:
                continue
            self.sources.append(s)
            seen.add(key)
        self.sources = sorted(self.sources, key=_canonical)

    #note: Ingest a full step output payload into the registry.
    def ingest_step_output(self, output: Dict[str, Any]) -> None:
        if not isinstance(output, dict):
            return
        self.add_entities(output.get("entities_delta") or [])
        self.add_relations(output.get("relations_delta") or [])
        self.add_findings(output.get("findings") or [])
        self.add_sources(output.get("sources") or [])

    #note: Return a JSON-serializable snapshot payload.
    def snapshot(self) -> Dict[str, Any]:
        return {
            "namespace": self.namespace,
            "id_policy": self.id_policy,
            "entities": [self.entities_by_id[k] for k in sorted(self.entities_by_id.keys())],
            "relations": list(self.relations),
            "findings": list(self.findings),
            "sources": list(self.sources),
        }

    #note: Simple lookup helper for downstream agents.
    def get_entity(self, entity_id: str) -> Optional[Dict[str, Any]]:
        return self.entities_by_id.get(entity_id)
