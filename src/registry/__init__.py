"""Entity registry and merge utilities."""

from src.registry.crossref_graph import build_crossref_graph
from src.registry.deduper import dedupe_entities
from src.registry.entity_key import build_entity_key
from src.registry.entity_registry import Entity, EntityRegistry, Relation
from src.registry.id_allocator import IdAllocator
from src.registry.merger import merge_registry
from src.registry.provenance import FieldProvenance

__all__ = [
    "Entity",
    "EntityRegistry",
    "FieldProvenance",
    "IdAllocator",
    "Relation",
    "build_crossref_graph",
    "build_entity_key",
    "dedupe_entities",
    "merge_registry",
]
