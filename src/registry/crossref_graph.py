"""
Cross-Reference Graph Management

This module manages the cross-reference graph that tracks relationships between entities
in the market intelligence pipeline. It provides functionality for:

- Building and maintaining entity relationship graphs
- Detecting circular references and dangling pointers
- Generating adjacency matrices for efficient lookups
- Validating graph integrity and consistency

The cross-reference graph is essential for:
- Ensuring referential integrity across the pipeline
- Enabling efficient relationship queries
- Supporting audit trails and governance requirements
- Generating comprehensive market intelligence reports
"""

from __future__ import annotations

import logging
from collections import defaultdict, deque
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set, Tuple

logger = logging.getLogger(__name__)


class CrossReferenceGraph:
    """
    Manages entity relationships and cross-references in the market intelligence pipeline.
    
    This class maintains a directed graph of entity relationships and provides methods
    for validation, analysis, and export of cross-reference data.
    """
    
    def __init__(self, run_id: str) -> None:
        """
        Initialize the cross-reference graph.
        
        Args:
            run_id: Unique identifier for the current pipeline run
        """
        self.run_id = run_id
        self.entities: Dict[str, Dict[str, Any]] = {}
        self.relations: List[Dict[str, Any]] = []
        self.adjacency_matrix: Dict[str, Dict[str, List[str]]] = defaultdict(lambda: defaultdict(list))
        self._validation_cache: Optional[Dict[str, Any]] = None
        
    def add_entity(self, entity_id: str, entity_data: Dict[str, Any]) -> None:
        """
        Add an entity to the graph.
        
        Args:
            entity_id: Unique entity identifier (TGT-001, MFR-001, CUS-001, etc.)
            entity_data: Entity metadata including type, name, domain, etc.
        """
        if not self._is_valid_entity_id(entity_id):
            raise ValueError(f"Invalid entity ID format: {entity_id}")
            
        self.entities[entity_id] = {
            "entity_id": entity_id,
            **entity_data
        }
        
        # Initialize adjacency matrix entry
        if entity_id not in self.adjacency_matrix:
            self.adjacency_matrix[entity_id] = defaultdict(list)
            
        # Clear validation cache
        self._validation_cache = None
        
        logger.debug(f"Added entity {entity_id} to cross-reference graph")
        
    def add_relation(self, from_entity_id: str, to_entity_id: str, 
                    relation_type: str, confidence: float = 1.0,
                    evidence_count: int = 1, discovered_by_step: str = "unknown") -> None:
        """
        Add a relationship between two entities.
        
        Args:
            from_entity_id: Source entity ID
            to_entity_id: Target entity ID
            relation_type: Type of relationship (peer_of, customer_of, etc.)
            confidence: Confidence score (0.0 to 1.0)
            evidence_count: Number of evidence sources supporting this relation
            discovered_by_step: Agent step that discovered this relation
        """
        if not self._is_valid_entity_id(from_entity_id):
            raise ValueError(f"Invalid from_entity_id format: {from_entity_id}")
        if not self._is_valid_entity_id(to_entity_id):
            raise ValueError(f"Invalid to_entity_id format: {to_entity_id}")
        if not self._is_valid_relation_type(relation_type):
            raise ValueError(f"Invalid relation type: {relation_type}")
        if not 0.0 <= confidence <= 1.0:
            raise ValueError(f"Confidence must be between 0.0 and 1.0, got: {confidence}")
            
        relation = {
            "from_entity_id": from_entity_id,
            "to_entity_id": to_entity_id,
            "relation_type": relation_type,
            "confidence": confidence,
            "evidence_count": evidence_count,
            "discovered_by_step": discovered_by_step
        }
        
        self.relations.append(relation)
        
        # Update adjacency matrix
        if relation_type not in self.adjacency_matrix[from_entity_id][to_entity_id]:
            self.adjacency_matrix[from_entity_id][to_entity_id].append(relation_type)
            
        # Clear validation cache
        self._validation_cache = None
        
        logger.debug(f"Added relation {from_entity_id} --{relation_type}--> {to_entity_id}")
        
    def validate_integrity(self) -> Dict[str, Any]:
        """
        Validate the integrity of the cross-reference graph.
        
        Returns:
            Dictionary containing validation results including:
            - integrity_check_passed: Boolean indicating overall success
            - dangling_references: List of entity IDs referenced but not defined
            - circular_references: List of circular reference chains
            - validation_timestamp_utc: Timestamp of validation
        """
        if self._validation_cache is not None:
            return self._validation_cache
            
        logger.info("Validating cross-reference graph integrity")
        
        # Find dangling references
        dangling_refs = self._find_dangling_references()
        
        # Find circular references
        circular_refs = self._find_circular_references()
        
        # Check for orphaned entities (entities with no relations)
        orphaned_entities = self._find_orphaned_entities()
        
        integrity_passed = len(dangling_refs) == 0 and len(circular_refs) == 0
        
        validation_result = {
            "integrity_check_passed": integrity_passed,
            "dangling_references": dangling_refs,
            "circular_references": circular_refs,
            "orphaned_entities": orphaned_entities,
            "validation_timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "total_entities": len(self.entities),
            "total_relations": len(self.relations)
        }
        
        self._validation_cache = validation_result
        
        if integrity_passed:
            logger.info("Cross-reference graph integrity validation PASSED")
        else:
            logger.warning(f"Cross-reference graph integrity validation FAILED: "
                         f"{len(dangling_refs)} dangling refs, {len(circular_refs)} circular refs")
            
        return validation_result
        
    def get_relations_for_entity(self, entity_id: str, 
                                relation_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get all relations for a specific entity.
        
        Args:
            entity_id: Entity ID to query
            relation_type: Optional filter by relation type
            
        Returns:
            List of relations involving the entity
        """
        relations = []
        
        for relation in self.relations:
            if (relation["from_entity_id"] == entity_id or 
                relation["to_entity_id"] == entity_id):
                if relation_type is None or relation["relation_type"] == relation_type:
                    relations.append(relation)
                    
        return relations
        
    def get_connected_entities(self, entity_id: str, 
                             relation_type: Optional[str] = None,
                             direction: str = "both") -> Set[str]:
        """
        Get all entities connected to a given entity.
        
        Args:
            entity_id: Source entity ID
            relation_type: Optional filter by relation type
            direction: "outgoing", "incoming", or "both"
            
        Returns:
            Set of connected entity IDs
        """
        connected = set()
        
        for relation in self.relations:
            if relation_type and relation["relation_type"] != relation_type:
                continue
                
            if direction in ("outgoing", "both") and relation["from_entity_id"] == entity_id:
                connected.add(relation["to_entity_id"])
            elif direction in ("incoming", "both") and relation["to_entity_id"] == entity_id:
                connected.add(relation["from_entity_id"])
                
        return connected
        
    def export_matrix(self) -> Dict[str, Any]:
        """
        Export the complete cross-reference matrix.
        
        Returns:
            Dictionary containing the full cross-reference matrix data
        """
        # Ensure validation is up to date
        validation_results = self.validate_integrity()
        
        # Get unique relation types
        relation_types = list(set(rel["relation_type"] for rel in self.relations))
        
        matrix_data = {
            "metadata": {
                "run_id": self.run_id,
                "generated_at_utc": datetime.now(timezone.utc).isoformat(),
                "total_entities": len(self.entities),
                "total_relations": len(self.relations),
                "relation_types": relation_types
            },
            "entities": self.entities.copy(),
            "relations": self.relations.copy(),
            "matrix": dict(self.adjacency_matrix),
            "validation_results": validation_results
        }
        
        logger.info(f"Exported cross-reference matrix with {len(self.entities)} entities "
                   f"and {len(self.relations)} relations")
        
        return matrix_data
        
    def _find_dangling_references(self) -> List[str]:
        """Find entity IDs that are referenced but not defined."""
        referenced_ids = set()
        defined_ids = set(self.entities.keys())
        
        for relation in self.relations:
            referenced_ids.add(relation["from_entity_id"])
            referenced_ids.add(relation["to_entity_id"])
            
        dangling = list(referenced_ids - defined_ids)
        return sorted(dangling)
        
    def _find_circular_references(self) -> List[List[str]]:
        """Find circular reference chains using DFS."""
        circular_refs = []
        visited = set()
        rec_stack = set()
        
        def dfs(entity_id: str, path: List[str]) -> None:
            if entity_id in rec_stack:
                # Found a cycle
                cycle_start = path.index(entity_id)
                cycle = path[cycle_start:] + [entity_id]
                circular_refs.append(cycle)
                return
                
            if entity_id in visited:
                return
                
            visited.add(entity_id)
            rec_stack.add(entity_id)
            
            # Follow outgoing relations
            for relation in self.relations:
                if relation["from_entity_id"] == entity_id:
                    dfs(relation["to_entity_id"], path + [entity_id])
                    
            rec_stack.remove(entity_id)
            
        for entity_id in self.entities:
            if entity_id not in visited:
                dfs(entity_id, [])
                
        return circular_refs
        
    def _find_orphaned_entities(self) -> List[str]:
        """Find entities with no incoming or outgoing relations."""
        entities_with_relations = set()
        
        for relation in self.relations:
            entities_with_relations.add(relation["from_entity_id"])
            entities_with_relations.add(relation["to_entity_id"])
            
        all_entities = set(self.entities.keys())
        orphaned = list(all_entities - entities_with_relations)
        
        return sorted(orphaned)
        
    def _is_valid_entity_id(self, entity_id: str) -> bool:
        """Validate entity ID format."""
        import re
        pattern = r"^(TGT|MFR|CUS)-[0-9]{3}$"
        return bool(re.match(pattern, entity_id))
        
    def _is_valid_relation_type(self, relation_type: str) -> bool:
        """Validate relation type."""
        valid_types = {"peer_of", "customer_of", "supplier_of", "partner_of", "competitor_of"}
        return relation_type in valid_types