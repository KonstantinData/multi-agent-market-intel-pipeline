"""
Cross-Reference Matrix Exporter

This module exports cross-reference matrices in various formats for downstream
consumption and stakeholder reporting. It provides functionality for:

- Exporting complete cross-reference matrices as JSON
- Generating human-readable relationship summaries
- Creating adjacency matrices for graph analysis
- Producing audit-ready relationship reports

The exported matrices are essential for:
- Stakeholder reporting and business intelligence
- Downstream system integration
- Audit trails and compliance documentation
- Graph analysis and visualization tools
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

from ..registry.crossref_graph import CrossReferenceGraph
from ..validator.crossref_validator import CrossReferenceValidator

logger = logging.getLogger(__name__)


class CrossReferenceMatrixExporter:
    """
    Exports cross-reference matrices and relationship data in various formats.
    
    This exporter creates comprehensive relationship matrices that can be consumed
    by downstream systems, reporting tools, and stakeholders.
    """
    
    def __init__(self, run_id: str, output_dir: Path) -> None:
        """
        Initialize the cross-reference matrix exporter.
        
        Args:
            run_id: Unique identifier for the current pipeline run
            output_dir: Directory where exports will be written
        """
        self.run_id = run_id
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
    def export_matrix(self, crossref_graph: CrossReferenceGraph, 
                     validate: bool = True) -> Dict[str, Any]:
        """
        Export the complete cross-reference matrix.
        
        Args:
            crossref_graph: Cross-reference graph to export
            validate: Whether to validate the matrix before export
            
        Returns:
            Dictionary containing export results and file paths
        """
        logger.info(f"Exporting cross-reference matrix for run {self.run_id}")
        
        try:
            # Get matrix data from graph
            matrix_data = crossref_graph.export_matrix()
            
            # Validate if requested
            if validate:
                validator = CrossReferenceValidator()
                validation_result = validator.validate_crossref_data(matrix_data)
                
                if validation_result["status"] == "FAIL":
                    logger.error("Cross-reference matrix validation failed, aborting export")
                    return {
                        "status": "FAILED",
                        "error": "Matrix validation failed",
                        "validation_result": validation_result
                    }
                elif validation_result["status"] == "WARN":
                    logger.warning("Cross-reference matrix validation has warnings")
                    
                # Update validation results in matrix data
                matrix_data["validation_results"] = validation_result
                
            # Export main matrix file
            matrix_file = self.output_dir / "crossref_matrix.json"
            self._write_json_file(matrix_file, matrix_data)
            
            # Export additional formats
            summary_file = self._export_summary(matrix_data)
            adjacency_file = self._export_adjacency_matrix(matrix_data)
            relationships_file = self._export_relationships_list(matrix_data)
            
            export_result = {
                "status": "SUCCESS",
                "run_id": self.run_id,
                "exported_at_utc": datetime.now(timezone.utc).isoformat(),
                "files": {
                    "matrix": str(matrix_file),
                    "summary": str(summary_file),
                    "adjacency": str(adjacency_file),
                    "relationships": str(relationships_file)
                },
                "statistics": {
                    "total_entities": len(matrix_data.get("entities", {})),
                    "total_relations": len(matrix_data.get("relations", [])),
                    "relation_types": matrix_data.get("metadata", {}).get("relation_types", [])
                }
            }
            
            logger.info(f"Cross-reference matrix export completed successfully")
            return export_result
            
        except Exception as e:
            logger.error(f"Cross-reference matrix export failed: {e}", exc_info=True)
            return {
                "status": "FAILED",
                "error": str(e),
                "run_id": self.run_id
            }
            
    def export_relations_summary(self, crossref_graph: CrossReferenceGraph) -> Dict[str, Any]:
        """
        Export a summary of relationships by type and entity.
        
        Args:
            crossref_graph: Cross-reference graph to summarize
            
        Returns:
            Dictionary containing relationship summaries
        """
        logger.debug("Generating relationships summary")
        
        matrix_data = crossref_graph.export_matrix()
        entities = matrix_data.get("entities", {})
        relations = matrix_data.get("relations", [])
        
        # Group relations by type
        relations_by_type = {}
        for relation in relations:
            rel_type = relation.get("relation_type")
            if rel_type not in relations_by_type:
                relations_by_type[rel_type] = []
            relations_by_type[rel_type].append(relation)
            
        # Generate entity summaries
        entity_summaries = {}
        for entity_id, entity_data in entities.items():
            outgoing_relations = crossref_graph.get_relations_for_entity(entity_id)
            outgoing_count = len([r for r in outgoing_relations if r["from_entity_id"] == entity_id])
            incoming_count = len([r for r in outgoing_relations if r["to_entity_id"] == entity_id])
            
            entity_summaries[entity_id] = {
                "entity_name": entity_data.get("entity_name"),
                "entity_type": entity_data.get("entity_type"),
                "outgoing_relations": outgoing_count,
                "incoming_relations": incoming_count,
                "total_relations": outgoing_count + incoming_count
            }
            
        summary = {
            "metadata": {
                "run_id": self.run_id,
                "generated_at_utc": datetime.now(timezone.utc).isoformat(),
                "total_entities": len(entities),
                "total_relations": len(relations)
            },
            "relations_by_type": {
                rel_type: {
                    "count": len(rels),
                    "relations": rels
                }
                for rel_type, rels in relations_by_type.items()
            },
            "entity_summaries": entity_summaries,
            "top_connected_entities": self._get_top_connected_entities(entity_summaries, 10)
        }
        
        # Export summary file
        summary_file = self.output_dir / "relationships_summary.json"
        self._write_json_file(summary_file, summary)
        
        return summary
        
    def _export_summary(self, matrix_data: Dict[str, Any]) -> Path:
        """Export a human-readable summary."""
        entities = matrix_data.get("entities", {})
        relations = matrix_data.get("relations", [])
        validation = matrix_data.get("validation_results", {})
        
        summary = {
            "run_id": self.run_id,
            "export_timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "overview": {
                "total_entities": len(entities),
                "total_relations": len(relations),
                "entities_by_type": self._count_entities_by_type(entities),
                "relations_by_type": self._count_relations_by_type(relations)
            },
            "validation_status": {
                "integrity_check_passed": validation.get("integrity_check_passed", False),
                "dangling_references_count": len(validation.get("dangling_references", [])),
                "circular_references_count": len(validation.get("circular_references", [])),
                "orphaned_entities_count": len(validation.get("orphaned_entities", []))
            },
            "key_insights": self._generate_key_insights(entities, relations)
        }
        
        summary_file = self.output_dir / "crossref_summary.json"
        self._write_json_file(summary_file, summary)
        return summary_file
        
    def _export_adjacency_matrix(self, matrix_data: Dict[str, Any]) -> Path:
        """Export pure adjacency matrix for graph analysis."""
        entities = matrix_data.get("entities", {})
        matrix = matrix_data.get("matrix", {})
        
        # Create ordered list of entity IDs
        entity_ids = sorted(entities.keys())
        
        # Build adjacency matrix
        adjacency = {
            "metadata": {
                "run_id": self.run_id,
                "generated_at_utc": datetime.now(timezone.utc).isoformat(),
                "entity_count": len(entity_ids),
                "entity_order": entity_ids
            },
            "matrix": {}
        }
        
        for from_id in entity_ids:
            adjacency["matrix"][from_id] = {}
            for to_id in entity_ids:
                relations = matrix.get(from_id, {}).get(to_id, [])
                adjacency["matrix"][from_id][to_id] = relations
                
        adjacency_file = self.output_dir / "adjacency_matrix.json"
        self._write_json_file(adjacency_file, adjacency)
        return adjacency_file
        
    def _export_relationships_list(self, matrix_data: Dict[str, Any]) -> Path:
        """Export flat list of relationships for easy consumption."""
        relations = matrix_data.get("relations", [])
        entities = matrix_data.get("entities", {})
        
        # Enrich relations with entity names
        enriched_relations = []
        for relation in relations:
            from_id = relation.get("from_entity_id")
            to_id = relation.get("to_entity_id")
            
            enriched_relation = {
                **relation,
                "from_entity_name": entities.get(from_id, {}).get("entity_name", "Unknown"),
                "to_entity_name": entities.get(to_id, {}).get("entity_name", "Unknown"),
                "from_entity_type": entities.get(from_id, {}).get("entity_type", "Unknown"),
                "to_entity_type": entities.get(to_id, {}).get("entity_type", "Unknown")
            }
            enriched_relations.append(enriched_relation)
            
        relationships_data = {
            "metadata": {
                "run_id": self.run_id,
                "generated_at_utc": datetime.now(timezone.utc).isoformat(),
                "total_relationships": len(enriched_relations)
            },
            "relationships": enriched_relations
        }
        
        relationships_file = self.output_dir / "relationships_list.json"
        self._write_json_file(relationships_file, relationships_data)
        return relationships_file
        
    def _count_entities_by_type(self, entities: Dict[str, Any]) -> Dict[str, int]:
        """Count entities by type."""
        counts = {}
        for entity_data in entities.values():
            entity_type = entity_data.get("entity_type", "unknown")
            counts[entity_type] = counts.get(entity_type, 0) + 1
        return counts
        
    def _count_relations_by_type(self, relations: List[Dict[str, Any]]) -> Dict[str, int]:
        """Count relations by type."""
        counts = {}
        for relation in relations:
            relation_type = relation.get("relation_type", "unknown")
            counts[relation_type] = counts.get(relation_type, 0) + 1
        return counts
        
    def _generate_key_insights(self, entities: Dict[str, Any], 
                             relations: List[Dict[str, Any]]) -> List[str]:
        """Generate key insights from the relationship data."""
        insights = []
        
        # Most connected entities
        connection_counts = {}
        for relation in relations:
            from_id = relation.get("from_entity_id")
            to_id = relation.get("to_entity_id")
            
            connection_counts[from_id] = connection_counts.get(from_id, 0) + 1
            connection_counts[to_id] = connection_counts.get(to_id, 0) + 1
            
        if connection_counts:
            most_connected = max(connection_counts.items(), key=lambda x: x[1])
            entity_name = entities.get(most_connected[0], {}).get("entity_name", most_connected[0])
            insights.append(f"Most connected entity: {entity_name} with {most_connected[1]} connections")
            
        # Relation type distribution
        relation_types = {}
        for relation in relations:
            rel_type = relation.get("relation_type", "unknown")
            relation_types[rel_type] = relation_types.get(rel_type, 0) + 1
            
        if relation_types:
            most_common_type = max(relation_types.items(), key=lambda x: x[1])
            insights.append(f"Most common relationship type: {most_common_type[0]} ({most_common_type[1]} instances)")
            
        # Entity type distribution
        entity_types = self._count_entities_by_type(entities)
        if entity_types:
            for entity_type, count in entity_types.items():
                insights.append(f"{entity_type.replace('_', ' ').title()}: {count} entities")
                
        return insights
        
    def _get_top_connected_entities(self, entity_summaries: Dict[str, Any], 
                                  limit: int = 10) -> List[Dict[str, Any]]:
        """Get top connected entities by total relation count."""
        sorted_entities = sorted(
            entity_summaries.items(),
            key=lambda x: x[1]["total_relations"],
            reverse=True
        )
        
        return [
            {
                "entity_id": entity_id,
                **summary
            }
            for entity_id, summary in sorted_entities[:limit]
        ]
        
    def _write_json_file(self, file_path: Path, data: Dict[str, Any]) -> None:
        """Write data to JSON file with proper formatting."""
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False, default=str)
            logger.debug(f"Wrote JSON file: {file_path}")
        except Exception as e:
            logger.error(f"Failed to write JSON file {file_path}: {e}")
            raise