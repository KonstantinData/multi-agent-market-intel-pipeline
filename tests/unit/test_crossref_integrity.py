"""
Unit tests for cross-reference integrity validation and management.

This test suite covers:
- Cross-reference graph construction and validation
- Entity relationship management
- Referential integrity checking
- Cross-reference matrix export functionality
- Validation error handling and edge cases
"""

import json
import pytest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import Mock, patch
from typing import Dict, Any, List

from src.registry.crossref_graph import CrossReferenceGraph
from src.validator.crossref_validator import CrossReferenceValidator
from src.exporters.crossref_matrix_exporter import CrossReferenceMatrixExporter


class TestCrossReferenceGraph:
    """Test cases for CrossReferenceGraph functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.run_id = "test_run_001"
        self.graph = CrossReferenceGraph(self.run_id)
        
    def test_add_entity_valid(self):
        """Test adding valid entities to the graph."""
        entity_data = {
            "entity_type": "target_company",
            "entity_name": "Test Company GmbH",
            "domain": "test-company.com"
        }
        
        self.graph.add_entity("TGT-001", entity_data)
        
        assert "TGT-001" in self.graph.entities
        assert self.graph.entities["TGT-001"]["entity_id"] == "TGT-001"
        assert self.graph.entities["TGT-001"]["entity_name"] == "Test Company GmbH"
        
    def test_add_entity_invalid_id(self):
        """Test adding entity with invalid ID format."""
        entity_data = {"entity_type": "target_company", "entity_name": "Test"}
        
        with pytest.raises(ValueError, match="Invalid entity ID format"):
            self.graph.add_entity("INVALID-ID", entity_data)
            
    def test_add_relation_valid(self):
        """Test adding valid relationships."""
        # Add entities first
        self.graph.add_entity("TGT-001", {"entity_type": "target_company", "entity_name": "Target"})
        self.graph.add_entity("CUS-001", {"entity_type": "customer", "entity_name": "Customer"})
        
        self.graph.add_relation("TGT-001", "CUS-001", "customer_of", 0.9, 2, "AG-40")
        
        assert len(self.graph.relations) == 1
        relation = self.graph.relations[0]
        assert relation["from_entity_id"] == "TGT-001"
        assert relation["to_entity_id"] == "CUS-001"
        assert relation["relation_type"] == "customer_of"
        assert relation["confidence"] == 0.9
        
    def test_add_relation_invalid_confidence(self):
        """Test adding relation with invalid confidence score."""
        self.graph.add_entity("TGT-001", {"entity_type": "target_company", "entity_name": "Target"})
        self.graph.add_entity("CUS-001", {"entity_type": "customer", "entity_name": "Customer"})
        
        with pytest.raises(ValueError, match="Confidence must be between 0.0 and 1.0"):
            self.graph.add_relation("TGT-001", "CUS-001", "customer_of", 1.5)
            
    def test_add_relation_invalid_type(self):
        """Test adding relation with invalid type."""
        self.graph.add_entity("TGT-001", {"entity_type": "target_company", "entity_name": "Target"})
        self.graph.add_entity("CUS-001", {"entity_type": "customer", "entity_name": "Customer"})
        
        with pytest.raises(ValueError, match="Invalid relation type"):
            self.graph.add_relation("TGT-001", "CUS-001", "invalid_relation")
            
    def test_validate_integrity_no_issues(self):
        """Test integrity validation with clean data."""
        # Add entities and relations
        self.graph.add_entity("TGT-001", {"entity_type": "target_company", "entity_name": "Target"})
        self.graph.add_entity("CUS-001", {"entity_type": "customer", "entity_name": "Customer"})
        self.graph.add_relation("TGT-001", "CUS-001", "customer_of")
        
        result = self.graph.validate_integrity()
        
        assert result["integrity_check_passed"] is True
        assert len(result["dangling_references"]) == 0
        assert len(result["circular_references"]) == 0
        
    def test_validate_integrity_dangling_references(self):
        """Test detection of dangling references."""
        self.graph.add_entity("TGT-001", {"entity_type": "target_company", "entity_name": "Target"})
        # Add relation to non-existent entity
        self.graph.relations.append({
            "from_entity_id": "TGT-001",
            "to_entity_id": "CUS-999",  # Does not exist
            "relation_type": "customer_of",
            "confidence": 1.0,
            "evidence_count": 1,
            "discovered_by_step": "test"
        })
        
        result = self.graph.validate_integrity()
        
        assert result["integrity_check_passed"] is False
        assert "CUS-999" in result["dangling_references"]
        
    def test_validate_integrity_circular_references(self):
        """Test detection of circular references."""
        # Create circular reference: A -> B -> C -> A
        entities = [
            ("TGT-001", {"entity_type": "target_company", "entity_name": "A"}),
            ("MFR-001", {"entity_type": "manufacturer", "entity_name": "B"}),
            ("CUS-001", {"entity_type": "customer", "entity_name": "C"})
        ]
        
        for entity_id, data in entities:
            self.graph.add_entity(entity_id, data)
            
        self.graph.add_relation("TGT-001", "MFR-001", "peer_of")
        self.graph.add_relation("MFR-001", "CUS-001", "customer_of")
        self.graph.add_relation("CUS-001", "TGT-001", "customer_of")  # Creates cycle
        
        result = self.graph.validate_integrity()
        
        # Circular references are detected but don't fail integrity (warnings only)
        assert len(result["circular_references"]) > 0
        
    def test_get_relations_for_entity(self):
        """Test retrieving relations for specific entity."""
        self.graph.add_entity("TGT-001", {"entity_type": "target_company", "entity_name": "Target"})
        self.graph.add_entity("CUS-001", {"entity_type": "customer", "entity_name": "Customer1"})
        self.graph.add_entity("CUS-002", {"entity_type": "customer", "entity_name": "Customer2"})
        
        self.graph.add_relation("TGT-001", "CUS-001", "customer_of")
        self.graph.add_relation("CUS-002", "TGT-001", "customer_of")
        
        relations = self.graph.get_relations_for_entity("TGT-001")
        
        assert len(relations) == 2
        entity_ids = {rel["from_entity_id"] for rel in relations} | {rel["to_entity_id"] for rel in relations}
        assert "TGT-001" in entity_ids
        
    def test_get_connected_entities(self):
        """Test retrieving connected entities."""
        self.graph.add_entity("TGT-001", {"entity_type": "target_company", "entity_name": "Target"})
        self.graph.add_entity("CUS-001", {"entity_type": "customer", "entity_name": "Customer"})
        self.graph.add_entity("MFR-001", {"entity_type": "manufacturer", "entity_name": "Manufacturer"})
        
        self.graph.add_relation("TGT-001", "CUS-001", "customer_of")
        self.graph.add_relation("MFR-001", "TGT-001", "peer_of")
        
        # Test outgoing connections
        outgoing = self.graph.get_connected_entities("TGT-001", direction="outgoing")
        assert "CUS-001" in outgoing
        assert "MFR-001" not in outgoing
        
        # Test incoming connections
        incoming = self.graph.get_connected_entities("TGT-001", direction="incoming")
        assert "MFR-001" in incoming
        assert "CUS-001" not in incoming
        
        # Test both directions
        both = self.graph.get_connected_entities("TGT-001", direction="both")
        assert "CUS-001" in both
        assert "MFR-001" in both
        
    def test_export_matrix(self):
        """Test matrix export functionality."""
        self.graph.add_entity("TGT-001", {"entity_type": "target_company", "entity_name": "Target"})
        self.graph.add_entity("CUS-001", {"entity_type": "customer", "entity_name": "Customer"})
        self.graph.add_relation("TGT-001", "CUS-001", "customer_of")
        
        matrix_data = self.graph.export_matrix()
        
        assert "metadata" in matrix_data
        assert "entities" in matrix_data
        assert "relations" in matrix_data
        assert "matrix" in matrix_data
        assert "validation_results" in matrix_data
        
        assert matrix_data["metadata"]["run_id"] == self.run_id
        assert matrix_data["metadata"]["total_entities"] == 2
        assert matrix_data["metadata"]["total_relations"] == 1


class TestCrossReferenceValidator:
    """Test cases for CrossReferenceValidator functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        # Create a mock schema path
        self.mock_schema = {
            "type": "object",
            "properties": {
                "metadata": {"type": "object"},
                "entities": {"type": "object"},
                "relations": {"type": "array"},
                "matrix": {"type": "object"},
                "validation_results": {"type": "object"}
            },
            "required": ["metadata", "entities", "relations", "matrix", "validation_results"]
        }
        
        with patch.object(CrossReferenceValidator, '_load_schema', return_value=self.mock_schema):
            self.validator = CrossReferenceValidator()
            
    def test_validate_crossref_data_valid(self):
        """Test validation of valid cross-reference data."""
        valid_data = {
            "metadata": {
                "run_id": "test_run",
                "generated_at_utc": "2024-12-01T12:00:00Z",
                "total_entities": 1,
                "total_relations": 0
            },
            "entities": {
                "TGT-001": {
                    "entity_id": "TGT-001",
                    "entity_type": "target_company",
                    "entity_name": "Test Company"
                }
            },
            "relations": [],
            "matrix": {},
            "validation_results": {
                "integrity_check_passed": True,
                "validation_timestamp_utc": "2024-12-01T12:00:00Z"
            }
        }
        
        result = self.validator.validate_crossref_data(valid_data)
        
        assert result["status"] == "PASS"
        assert len(result["errors"]) == 0
        
    def test_validate_crossref_data_invalid_entity_id(self):
        """Test validation with invalid entity ID format."""
        invalid_data = {
            "metadata": {"run_id": "test", "generated_at_utc": "2024-12-01T12:00:00Z", "total_entities": 1, "total_relations": 0},
            "entities": {
                "INVALID-ID": {
                    "entity_id": "INVALID-ID",
                    "entity_type": "target_company",
                    "entity_name": "Test"
                }
            },
            "relations": [],
            "matrix": {},
            "validation_results": {"integrity_check_passed": True, "validation_timestamp_utc": "2024-12-01T12:00:00Z"}
        }
        
        result = self.validator.validate_crossref_data(invalid_data)
        
        assert result["status"] == "FAIL"
        assert any("Invalid entity ID format" in error for error in result["errors"])
        
    def test_validate_crossref_data_dangling_reference(self):
        """Test validation with dangling references."""
        data_with_dangling = {
            "metadata": {"run_id": "test", "generated_at_utc": "2024-12-01T12:00:00Z", "total_entities": 1, "total_relations": 1},
            "entities": {
                "TGT-001": {
                    "entity_id": "TGT-001",
                    "entity_type": "target_company",
                    "entity_name": "Test"
                }
            },
            "relations": [
                {
                    "from_entity_id": "TGT-001",
                    "to_entity_id": "CUS-999",  # Does not exist
                    "relation_type": "customer_of",
                    "confidence": 1.0,
                    "evidence_count": 1,
                    "discovered_by_step": "AG-40"
                }
            ],
            "matrix": {},
            "validation_results": {"integrity_check_passed": True, "validation_timestamp_utc": "2024-12-01T12:00:00Z"}
        }
        
        result = self.validator.validate_crossref_data(data_with_dangling)
        
        assert result["status"] == "FAIL"
        assert any("Dangling reference" in error for error in result["errors"])
        
    def test_validate_relations_delta_valid(self):
        """Test validation of valid relations delta."""
        relations_delta = [
            {
                "from_entity_id": "TGT-001",
                "to_entity_id": "CUS-001",
                "relation_type": "customer_of",
                "confidence": 0.9,
                "evidence_count": 2
            }
        ]
        
        entity_registry = {
            "TGT-001": {"entity_type": "target_company"},
            "CUS-001": {"entity_type": "customer"}
        }
        
        result = self.validator.validate_relations_delta(relations_delta, entity_registry)
        
        assert result["status"] == "PASS"
        assert len(result["errors"]) == 0
        
    def test_validate_relations_delta_missing_fields(self):
        """Test validation with missing required fields."""
        relations_delta = [
            {
                "from_entity_id": "TGT-001",
                # Missing to_entity_id and relation_type
                "confidence": 0.9
            }
        ]
        
        result = self.validator.validate_relations_delta(relations_delta, {})
        
        assert result["status"] == "FAIL"
        assert any("Missing required field" in error for error in result["errors"])
        
    def test_validate_relations_delta_entity_not_found(self):
        """Test validation with entities not in registry."""
        relations_delta = [
            {
                "from_entity_id": "TGT-001",
                "to_entity_id": "CUS-001",
                "relation_type": "customer_of"
            }
        ]
        
        entity_registry = {}  # Empty registry
        
        result = self.validator.validate_relations_delta(relations_delta, entity_registry)
        
        assert result["status"] == "WARN"  # Warnings for missing entities
        assert any("not found in registry" in warning for warning in result["warnings"])


class TestCrossReferenceMatrixExporter:
    """Test cases for CrossReferenceMatrixExporter functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.run_id = "test_run_001"
        self.output_dir = Path("/tmp/test_crossref_export")
        self.exporter = CrossReferenceMatrixExporter(self.run_id, self.output_dir)
        
        # Create test graph
        self.graph = CrossReferenceGraph(self.run_id)
        self.graph.add_entity("TGT-001", {
            "entity_type": "target_company",
            "entity_name": "Target Company",
            "domain": "target.com"
        })
        self.graph.add_entity("CUS-001", {
            "entity_type": "customer", 
            "entity_name": "Customer Company",
            "domain": "customer.com"
        })
        self.graph.add_relation("TGT-001", "CUS-001", "customer_of", 0.9, 2, "AG-40")
        
    @patch('pathlib.Path.mkdir')
    @patch('builtins.open')
    @patch('json.dump')
    def test_export_matrix_success(self, mock_json_dump, mock_open, mock_mkdir):
        """Test successful matrix export."""
        mock_file = Mock()
        mock_open.return_value.__enter__.return_value = mock_file
        
        result = self.exporter.export_matrix(self.graph, validate=False)
        
        assert result["status"] == "SUCCESS"
        assert result["run_id"] == self.run_id
        assert "files" in result
        assert "statistics" in result
        
        # Verify files were written
        assert mock_json_dump.call_count >= 4  # matrix, summary, adjacency, relationships
        
    @patch('pathlib.Path.mkdir')
    def test_export_matrix_validation_failure(self, mock_mkdir):
        """Test export with validation failure."""
        # Create graph with dangling reference
        bad_graph = CrossReferenceGraph(self.run_id)
        bad_graph.add_entity("TGT-001", {"entity_type": "target_company", "entity_name": "Target"})
        bad_graph.relations.append({
            "from_entity_id": "TGT-001",
            "to_entity_id": "CUS-999",  # Does not exist
            "relation_type": "customer_of",
            "confidence": 1.0,
            "evidence_count": 1,
            "discovered_by_step": "test"
        })
        
        result = self.exporter.export_matrix(bad_graph, validate=True)
        
        assert result["status"] == "FAILED"
        assert "validation failed" in result["error"].lower()
        
    @patch('pathlib.Path.mkdir')
    @patch('builtins.open')
    @patch('json.dump')
    def test_export_relations_summary(self, mock_json_dump, mock_open, mock_mkdir):
        """Test relations summary export."""
        mock_file = Mock()
        mock_open.return_value.__enter__.return_value = mock_file
        
        summary = self.exporter.export_relations_summary(self.graph)
        
        assert "metadata" in summary
        assert "relations_by_type" in summary
        assert "entity_summaries" in summary
        assert summary["metadata"]["run_id"] == self.run_id
        
        # Verify customer_of relation is in summary
        assert "customer_of" in summary["relations_by_type"]
        assert summary["relations_by_type"]["customer_of"]["count"] == 1


class TestCrossReferenceIntegration:
    """Integration tests for cross-reference system components."""
    
    def test_end_to_end_workflow(self):
        """Test complete workflow from graph creation to export."""
        run_id = "integration_test_001"
        
        # 1. Create and populate graph
        graph = CrossReferenceGraph(run_id)
        
        # Add entities
        entities = [
            ("TGT-001", {"entity_type": "target_company", "entity_name": "Target Corp", "domain": "target.com"}),
            ("MFR-001", {"entity_type": "manufacturer", "entity_name": "Manufacturer Inc", "domain": "mfr.com"}),
            ("CUS-001", {"entity_type": "customer", "entity_name": "Customer LLC", "domain": "customer.com"}),
            ("CUS-002", {"entity_type": "customer", "entity_name": "Customer2 GmbH", "domain": "customer2.com"})
        ]
        
        for entity_id, data in entities:
            graph.add_entity(entity_id, data)
            
        # Add relationships
        relationships = [
            ("TGT-001", "CUS-001", "customer_of", 0.9, 3, "AG-40"),
            ("TGT-001", "CUS-002", "customer_of", 0.8, 2, "AG-40"),
            ("TGT-001", "MFR-001", "peer_of", 0.7, 1, "AG-41"),
            ("MFR-001", "CUS-001", "customer_of", 0.6, 1, "AG-42")
        ]
        
        for from_id, to_id, rel_type, confidence, evidence, step in relationships:
            graph.add_relation(from_id, to_id, rel_type, confidence, evidence, step)
            
        # 2. Validate integrity
        validation_result = graph.validate_integrity()
        assert validation_result["integrity_check_passed"] is True
        
        # 3. Validate with validator
        with patch.object(CrossReferenceValidator, '_load_schema', return_value={"type": "object"}):
            validator = CrossReferenceValidator()
            matrix_data = graph.export_matrix()
            validator_result = validator.validate_crossref_data(matrix_data)
            assert validator_result["status"] in ["PASS", "WARN"]
            
        # 4. Export matrix
        with patch('pathlib.Path.mkdir'), \
             patch('builtins.open'), \
             patch('json.dump'):
            
            exporter = CrossReferenceMatrixExporter(run_id, Path("/tmp/test"))
            export_result = exporter.export_matrix(graph, validate=False)
            
            assert export_result["status"] == "SUCCESS"
            assert export_result["statistics"]["total_entities"] == 4
            assert export_result["statistics"]["total_relations"] == 4
            
        # 5. Verify relationship queries
        target_relations = graph.get_relations_for_entity("TGT-001")
        assert len(target_relations) == 3  # TGT-001 appears in 3 relations
        
        target_customers = graph.get_connected_entities("TGT-001", "customer_of", "outgoing")
        assert "CUS-001" in target_customers
        assert "CUS-002" in target_customers
        assert len(target_customers) == 2
        
    def test_validation_error_propagation(self):
        """Test that validation errors are properly propagated through the system."""
        run_id = "error_test_001"
        graph = CrossReferenceGraph(run_id)
        
        # Create scenario with validation errors
        graph.add_entity("TGT-001", {"entity_type": "target_company", "entity_name": "Target"})
        
        # Add relation to non-existent entity (dangling reference)
        graph.relations.append({
            "from_entity_id": "TGT-001",
            "to_entity_id": "CUS-999",
            "relation_type": "customer_of",
            "confidence": 1.0,
            "evidence_count": 1,
            "discovered_by_step": "test"
        })
        
        # Validation should detect the error
        validation_result = graph.validate_integrity()
        assert validation_result["integrity_check_passed"] is False
        assert "CUS-999" in validation_result["dangling_references"]
        
        # Export with validation should fail
        with patch('pathlib.Path.mkdir'):
            exporter = CrossReferenceMatrixExporter(run_id, Path("/tmp/test"))
            export_result = exporter.export_matrix(graph, validate=True)
            
            assert export_result["status"] == "FAILED"
            assert "validation" in export_result["error"].lower()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])