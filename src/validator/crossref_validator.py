"""
Cross-Reference Validator

This module provides validation functionality for cross-reference integrity in the
market intelligence pipeline. It ensures that all entity relationships are valid,
consistent, and maintain referential integrity.

Key validation functions:
- Validate entity ID formats and consistency
- Check for dangling references (references to non-existent entities)
- Detect circular dependencies that could cause infinite loops
- Verify relation type consistency and business rules
- Ensure cross-reference schema compliance

This validator is critical for maintaining data quality and preventing
downstream errors in the pipeline.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

import jsonschema

from ..registry.crossref_graph import CrossReferenceGraph

logger = logging.getLogger(__name__)


class CrossReferenceValidator:
    """
    Validates cross-reference integrity and consistency in the market intelligence pipeline.
    
    This validator ensures that all entity relationships maintain referential integrity
    and comply with business rules and schema requirements.
    """
    
    def __init__(self, schema_path: Optional[Path] = None) -> None:
        """
        Initialize the cross-reference validator.
        
        Args:
            schema_path: Path to the cross-reference schema file
        """
        self.schema_path = schema_path or self._get_default_schema_path()
        self.schema = self._load_schema()
        self._business_rules = self._load_business_rules()
        
    def validate_crossref_data(self, crossref_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate complete cross-reference data structure.
        
        Args:
            crossref_data: Cross-reference matrix data to validate
            
        Returns:
            Validation result with status, errors, and warnings
        """
        logger.info("Starting cross-reference data validation")
        
        validation_result = {
            "status": "PASS",
            "errors": [],
            "warnings": [],
            "validation_timestamp_utc": crossref_data.get("validation_results", {}).get("validation_timestamp_utc"),
            "checks_performed": []
        }
        
        try:
            # 1. Schema validation
            self._validate_schema(crossref_data, validation_result)
            
            # 2. Entity ID format validation
            self._validate_entity_ids(crossref_data, validation_result)
            
            # 3. Referential integrity validation
            self._validate_referential_integrity(crossref_data, validation_result)
            
            # 4. Business rules validation
            self._validate_business_rules(crossref_data, validation_result)
            
            # 5. Matrix consistency validation
            self._validate_matrix_consistency(crossref_data, validation_result)
            
            # 6. Relation type validation
            self._validate_relation_types(crossref_data, validation_result)
            
        except Exception as e:
            validation_result["status"] = "FAIL"
            validation_result["errors"].append(f"Validation failed with exception: {str(e)}")
            logger.error(f"Cross-reference validation failed: {e}", exc_info=True)
            
        # Set final status
        if validation_result["errors"]:
            validation_result["status"] = "FAIL"
        elif validation_result["warnings"]:
            validation_result["status"] = "WARN"
            
        logger.info(f"Cross-reference validation completed with status: {validation_result['status']}")
        return validation_result
        
    def validate_relations_delta(self, relations_delta: List[Dict[str, Any]], 
                                entity_registry: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate a relations delta from an agent step.
        
        Args:
            relations_delta: List of relations to validate
            entity_registry: Current entity registry for reference checking
            
        Returns:
            Validation result
        """
        logger.debug(f"Validating relations delta with {len(relations_delta)} relations")
        
        validation_result = {
            "status": "PASS",
            "errors": [],
            "warnings": [],
            "checks_performed": ["relations_delta_validation"]
        }
        
        entity_ids = set(entity_registry.keys())
        
        for i, relation in enumerate(relations_delta):
            try:
                # Validate required fields
                required_fields = ["from_entity_id", "to_entity_id", "relation_type"]
                for field in required_fields:
                    if field not in relation:
                        validation_result["errors"].append(
                            f"Relation {i}: Missing required field '{field}'"
                        )
                        continue
                        
                # Validate entity ID formats
                from_id = relation.get("from_entity_id")
                to_id = relation.get("to_entity_id")
                
                if from_id and not self._is_valid_entity_id(from_id):
                    validation_result["errors"].append(
                        f"Relation {i}: Invalid from_entity_id format: {from_id}"
                    )
                    
                if to_id and not self._is_valid_entity_id(to_id):
                    validation_result["errors"].append(
                        f"Relation {i}: Invalid to_entity_id format: {to_id}"
                    )
                    
                # Check entity existence (warn if not found, as they might be added later)
                if from_id and from_id not in entity_ids:
                    validation_result["warnings"].append(
                        f"Relation {i}: from_entity_id '{from_id}' not found in registry"
                    )
                    
                if to_id and to_id not in entity_ids:
                    validation_result["warnings"].append(
                        f"Relation {i}: to_entity_id '{to_id}' not found in registry"
                    )
                    
                # Validate relation type
                relation_type = relation.get("relation_type")
                if relation_type and not self._is_valid_relation_type(relation_type):
                    validation_result["errors"].append(
                        f"Relation {i}: Invalid relation_type: {relation_type}"
                    )
                    
                # Validate confidence if present
                confidence = relation.get("confidence")
                if confidence is not None and not (0.0 <= confidence <= 1.0):
                    validation_result["errors"].append(
                        f"Relation {i}: Confidence must be between 0.0 and 1.0, got: {confidence}"
                    )
                    
            except Exception as e:
                validation_result["errors"].append(
                    f"Relation {i}: Validation error: {str(e)}"
                )
                
        # Set final status
        if validation_result["errors"]:
            validation_result["status"] = "FAIL"
        elif validation_result["warnings"]:
            validation_result["status"] = "WARN"
            
        return validation_result
        
    def _validate_schema(self, data: Dict[str, Any], result: Dict[str, Any]) -> None:
        """Validate against JSON schema."""
        result["checks_performed"].append("schema_validation")
        
        try:
            jsonschema.validate(data, self.schema)
            logger.debug("Schema validation passed")
        except jsonschema.ValidationError as e:
            result["errors"].append(f"Schema validation failed: {e.message}")
            logger.error(f"Schema validation error: {e.message}")
        except Exception as e:
            result["errors"].append(f"Schema validation error: {str(e)}")
            logger.error(f"Schema validation exception: {e}")
            
    def _validate_entity_ids(self, data: Dict[str, Any], result: Dict[str, Any]) -> None:
        """Validate entity ID formats and consistency."""
        result["checks_performed"].append("entity_id_validation")
        
        entities = data.get("entities", {})
        
        for entity_id, entity_data in entities.items():
            # Check ID format
            if not self._is_valid_entity_id(entity_id):
                result["errors"].append(f"Invalid entity ID format: {entity_id}")
                
            # Check consistency between key and entity_id field
            if entity_data.get("entity_id") != entity_id:
                result["errors"].append(
                    f"Entity ID mismatch: key='{entity_id}', entity_id='{entity_data.get('entity_id')}'"
                )
                
            # Check entity type consistency with ID prefix
            entity_type = entity_data.get("entity_type")
            expected_prefix = self._get_expected_prefix(entity_type)
            if expected_prefix and not entity_id.startswith(expected_prefix):
                result["errors"].append(
                    f"Entity ID prefix mismatch: {entity_id} should start with {expected_prefix} for type {entity_type}"
                )
                
    def _validate_referential_integrity(self, data: Dict[str, Any], result: Dict[str, Any]) -> None:
        """Validate referential integrity."""
        result["checks_performed"].append("referential_integrity_validation")
        
        entities = data.get("entities", {})
        relations = data.get("relations", [])
        entity_ids = set(entities.keys())
        
        # Check for dangling references
        for relation in relations:
            from_id = relation.get("from_entity_id")
            to_id = relation.get("to_entity_id")
            
            if from_id and from_id not in entity_ids:
                result["errors"].append(f"Dangling reference: from_entity_id '{from_id}' not found")
                
            if to_id and to_id not in entity_ids:
                result["errors"].append(f"Dangling reference: to_entity_id '{to_id}' not found")
                
        # Use validation results from the graph if available
        validation_results = data.get("validation_results", {})
        if not validation_results.get("integrity_check_passed", True):
            dangling_refs = validation_results.get("dangling_references", [])
            for ref in dangling_refs:
                result["errors"].append(f"Dangling reference detected: {ref}")
                
            circular_refs = validation_results.get("circular_references", [])
            for cycle in circular_refs:
                result["warnings"].append(f"Circular reference detected: {' -> '.join(cycle)}")
                
    def _validate_business_rules(self, data: Dict[str, Any], result: Dict[str, Any]) -> None:
        """Validate business rules."""
        result["checks_performed"].append("business_rules_validation")
        
        relations = data.get("relations", [])
        
        # Rule: Target company should not be customer of itself
        target_entities = [eid for eid in data.get("entities", {}) if eid.startswith("TGT-")]
        
        for relation in relations:
            from_id = relation.get("from_entity_id")
            to_id = relation.get("to_entity_id")
            relation_type = relation.get("relation_type")
            
            # Self-reference check
            if from_id == to_id:
                result["warnings"].append(f"Self-reference detected: {from_id} -> {to_id}")
                
            # Target company business rules
            if from_id in target_entities and to_id in target_entities:
                if relation_type == "customer_of":
                    result["warnings"].append(
                        f"Target company as customer of target company: {from_id} -> {to_id}"
                    )
                    
        # Rule: Check for conflicting relations
        relation_pairs = {}
        for relation in relations:
            key = (relation.get("from_entity_id"), relation.get("to_entity_id"))
            if key not in relation_pairs:
                relation_pairs[key] = []
            relation_pairs[key].append(relation.get("relation_type"))
            
        for (from_id, to_id), types in relation_pairs.items():
            if len(set(types)) > 1:
                result["warnings"].append(
                    f"Multiple relation types between {from_id} and {to_id}: {types}"
                )
                
    def _validate_matrix_consistency(self, data: Dict[str, Any], result: Dict[str, Any]) -> None:
        """Validate matrix consistency with relations list."""
        result["checks_performed"].append("matrix_consistency_validation")
        
        relations = data.get("relations", [])
        matrix = data.get("matrix", {})
        
        # Build expected matrix from relations
        expected_matrix = {}
        for relation in relations:
            from_id = relation.get("from_entity_id")
            to_id = relation.get("to_entity_id")
            relation_type = relation.get("relation_type")
            
            if from_id not in expected_matrix:
                expected_matrix[from_id] = {}
            if to_id not in expected_matrix[from_id]:
                expected_matrix[from_id][to_id] = []
                
            if relation_type not in expected_matrix[from_id][to_id]:
                expected_matrix[from_id][to_id].append(relation_type)
                
        # Compare with actual matrix
        for from_id, targets in expected_matrix.items():
            if from_id not in matrix:
                result["errors"].append(f"Matrix missing entry for entity: {from_id}")
                continue
                
            for to_id, expected_types in targets.items():
                actual_types = matrix[from_id].get(to_id, [])
                
                for expected_type in expected_types:
                    if expected_type not in actual_types:
                        result["errors"].append(
                            f"Matrix missing relation: {from_id} --{expected_type}--> {to_id}"
                        )
                        
    def _validate_relation_types(self, data: Dict[str, Any], result: Dict[str, Any]) -> None:
        """Validate relation types."""
        result["checks_performed"].append("relation_type_validation")
        
        valid_types = {"peer_of", "customer_of", "supplier_of", "partner_of", "competitor_of"}
        relations = data.get("relations", [])
        
        for i, relation in enumerate(relations):
            relation_type = relation.get("relation_type")
            if relation_type and relation_type not in valid_types:
                result["errors"].append(
                    f"Relation {i}: Invalid relation type '{relation_type}'. "
                    f"Valid types: {sorted(valid_types)}"
                )
                
    def _load_schema(self) -> Dict[str, Any]:
        """Load the cross-reference schema."""
        try:
            with open(self.schema_path, 'r', encoding='utf-8') as f:
                schema = json.load(f)
            logger.debug(f"Loaded cross-reference schema from {self.schema_path}")
            return schema
        except Exception as e:
            logger.error(f"Failed to load schema from {self.schema_path}: {e}")
            # Return minimal schema as fallback
            return {"type": "object"}
            
    def _load_business_rules(self) -> Dict[str, Any]:
        """Load business rules configuration."""
        # For now, return hardcoded rules
        # In the future, this could load from a configuration file
        return {
            "allow_self_references": False,
            "allow_circular_references": True,  # With warnings
            "max_relation_types_per_pair": 3,
            "required_confidence_threshold": 0.1
        }
        
    def _get_default_schema_path(self) -> Path:
        """Get the default schema path."""
        # Assume we're in src/validator/ and need to go to configs/contracts/
        current_file = Path(__file__)
        repo_root = current_file.parent.parent.parent
        return repo_root / "configs" / "contracts" / "crossref_schema.json"
        
    def _is_valid_entity_id(self, entity_id: str) -> bool:
        """Validate entity ID format."""
        import re
        pattern = r"^(TGT|MFR|CUS)-[0-9]{3}$"
        return bool(re.match(pattern, entity_id))
        
    def _is_valid_relation_type(self, relation_type: str) -> bool:
        """Validate relation type."""
        valid_types = {"peer_of", "customer_of", "supplier_of", "partner_of", "competitor_of"}
        return relation_type in valid_types
        
    def _get_expected_prefix(self, entity_type: str) -> Optional[str]:
        """Get expected ID prefix for entity type."""
        prefix_map = {
            "target_company": "TGT-",
            "manufacturer": "MFR-",
            "customer": "CUS-"
        }
        return prefix_map.get(entity_type)