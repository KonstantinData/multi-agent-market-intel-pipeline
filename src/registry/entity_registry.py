from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class Entity:
    entity_id: str
    entity_type: str
    entity_name: str
    domain: Optional[str]
    entity_key: str
    attributes: Dict[str, Any] = field(default_factory=dict)
    sources: List[Dict[str, Any]] = field(default_factory=list)

    @classmethod
    def from_dict(cls, payload: Dict[str, Any]) -> "Entity":
        return cls(
            entity_id=str(payload.get("entity_id", "")),
            entity_type=str(payload.get("entity_type", "")),
            entity_name=str(payload.get("entity_name", "")),
            domain=payload.get("domain"),
            entity_key=str(payload.get("entity_key", "")),
            attributes=dict(payload.get("attributes", {})),
            sources=list(payload.get("sources", [])),
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "entity_id": self.entity_id,
            "entity_type": self.entity_type,
            "entity_name": self.entity_name,
            "domain": self.domain,
            "entity_key": self.entity_key,
            "attributes": self.attributes,
            "sources": self.sources,
        }


@dataclass
class Relation:
    source_id: str
    relation_type: str
    target_id: str
    evidence: List[Dict[str, Any]] = field(default_factory=list)

    @classmethod
    def from_dict(cls, payload: Dict[str, Any]) -> "Relation":
        return cls(
            source_id=str(payload.get("source_id", "")),
            relation_type=str(payload.get("relation_type", "")),
            target_id=str(payload.get("target_id", "")),
            evidence=list(payload.get("evidence", [])),
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "source_id": self.source_id,
            "relation_type": self.relation_type,
            "target_id": self.target_id,
            "evidence": self.evidence,
        }


@dataclass
class EntityRegistry:
    entities_by_id: Dict[str, Entity] = field(default_factory=dict)
    entities_by_key: Dict[str, str] = field(default_factory=dict)
    relations: List[Relation] = field(default_factory=list)

    def add_entity(self, entity: Entity) -> None:
        self.entities_by_id[entity.entity_id] = entity
        if entity.entity_key:
            self.entities_by_key[entity.entity_key] = entity.entity_id

    def get_by_key(self, entity_key: str) -> Optional[Entity]:
        entity_id = self.entities_by_key.get(entity_key)
        if not entity_id:
            return None
        return self.entities_by_id.get(entity_id)

    def add_relation(self, relation: Relation) -> None:
        self.relations.append(relation)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "entities": [entity.to_dict() for entity in self.entities_by_id.values()],
            "relations": [relation.to_dict() for relation in self.relations],
        }
