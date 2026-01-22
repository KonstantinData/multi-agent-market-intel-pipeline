"""
AG-15 Network Mapper Agent

Responsible for expanding the lead universe by identifying related companies
based on the Intake Company's business segment and customer base.
"""

from datetime import datetime, timezone
from typing import Dict, Any, Optional

from ..common.base_agent import BaseAgent, AgentResult


class AG15NetworkMapper(BaseAgent):
    """
    Agent responsible for network discovery and relationship mapping.
    
    Key Functions:
    - Network Discovery (peer companies, downstream customers)
    - Relationship Mapping (explicit connections via relations_delta)
    - Strategic Sourcing (verify business sectors and supply chain connections)
    """
    
    def __init__(self):
        super().__init__()
        self.agent_id = "AG-15"
        self.agent_name = "ag15_network_mapper"
        self.core_industries = ["Medical Technology", "Mechanical Engineering", "Electrical Engineering"]
    
    def run(
        self,
        case_input: Dict[str, Any],
        meta_case_normalized: Dict[str, Any],
        meta_target_entity_stub: Dict[str, Any],
        registry_snapshot: Optional[Dict[str, Any]] = None,
    ) -> AgentResult:
        """
        Execute network mapping for the target company.
        
        Args:
            case_input: Original case input
            meta_case_normalized: Normalized case input from AG-00
            meta_target_entity_stub: Target entity information from AG-00
            registry_snapshot: Current registry state
            
        Returns:
            AgentResult with network mapping output
        """
        company_name = meta_case_normalized.get("company_name_canonical", "")
        domain = meta_case_normalized.get("web_domain_normalized", "")
        
        # Initialize output structure
        output = {
            "step_meta": self._create_step_meta(),
            "entities_delta": {},
            "relations_delta": {},
            "findings": {},
            "sources": []
        }
        
        try:
            # Perform network research
            network_data = self._research_network_connections(company_name, domain, meta_target_entity_stub)
            
            if network_data:
                output["entities_delta"] = network_data["entities"]
                output["relations_delta"] = network_data["relations"]
                output["findings"] = network_data["findings"]
                output["sources"] = network_data["sources"]
            
        except Exception as e:
            self.logger.error(f"Error in AG-15 execution: {str(e)}")
            output["findings"] = {"error": f"Network mapping failed: {str(e)}"}
        
        return AgentResult(ok=True, output=output)
    
    def _research_network_connections(self, company_name: str, domain: str, target_entity: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Research network connections for the target company.
        
        Args:
            company_name: Company name
            domain: Company domain
            target_entity: Target entity information
            
        Returns:
            Network data structure or None if not found
        """
        # Search queries for network discovery
        search_queries = [
            f"{company_name} competitors same industry",
            f"{company_name} suppliers customers business partners",
            f"{company_name} industry peers mechanical engineering",
            f"{company_name} supply chain network",
            f"{company_name} business relationships"
        ]
        
        sources = []
        entities_delta = {}
        relations_delta = {}
        
        # Collect sources
        for query in search_queries:
            source_url = f"https://example-industry-database.com/search?q={query.replace(' ', '+')}"
            sources.append({
                "publisher": "Industry Network Database",
                "url": source_url,
                "title": f"Network research for {company_name}",
                "accessed_at_utc": datetime.now(timezone.utc).isoformat()
            })
        
        # Example network discovery (would be populated from actual research)
        if company_name and domain:
            # Discover peer companies
            peer_companies = self._discover_peer_companies(company_name)
            customer_companies = self._discover_customer_companies(company_name)
            
            # Build entities delta
            all_discovered = {**peer_companies, **customer_companies}
            entities_delta = all_discovered
            
            # Build relations delta
            relations_delta = self._build_relations(target_entity.get("entity_key", ""), all_discovered)
        
        findings = {
            "network_expansion_summary": f"Identified {len(entities_delta)} related companies for {company_name}",
            "peer_count": len([e for e in entities_delta.values() if e.get("relationship_type") == "peer"]),
            "customer_count": len([e for e in entities_delta.values() if e.get("relationship_type") == "customer"]),
            "inventory_overlap_rationale": "Companies in same sector likely share inventory requirements",
            "replacement_parts_rationale": "Downstream customers may need replacement parts"
        }
        
        return {
            "entities": entities_delta,
            "relations": relations_delta,
            "findings": findings,
            "sources": sources
        }
    
    def _discover_peer_companies(self, company_name: str) -> Dict[str, Any]:
        """Discover peer companies in the same industry."""
        # Placeholder for actual peer discovery
        return {
            "PEER-001": {
                "entity_key": "peer-competitor-001",
                "entity_name": "Competitor Solutions Inc.",
                "industry": "Mechanical Engineering",
                "relationship_type": "peer",
                "rationale": "Same business sector - likely inventory overlap"
            }
        }
    
    def _discover_customer_companies(self, company_name: str) -> Dict[str, Any]:
        """Discover customer companies (buyers)."""
        # Placeholder for actual customer discovery
        return {
            "CUSTOMER-001": {
                "entity_key": "customer-buyer-001", 
                "entity_name": "Industrial Buyer Corp.",
                "industry": "Manufacturing",
                "relationship_type": "customer",
                "rationale": "Downstream buyer - replacement parts need"
            }
        }
    
    def _build_relations(self, source_entity_key: str, discovered_entities: Dict[str, Any]) -> Dict[str, Any]:
        """Build relations delta from discovered entities."""
        relations = {}
        
        for entity_id, entity_data in discovered_entities.items():
            relation_id = f"REL-{entity_id}"
            relationship_type = entity_data.get("relationship_type", "unknown")
            
            if relationship_type == "peer":
                relation_type = "Same Business Sector"
            elif relationship_type == "customer":
                relation_type = "Supplier to"
            else:
                relation_type = "Business Network"
            
            relations[relation_id] = {
                "relationship_id": relation_id,
                "source_id": source_entity_key,
                "target_id": entity_data.get("entity_key", ""),
                "type": relation_type,
                "rationale": entity_data.get("rationale", "n/v")
            }
        
        return relations
    
    def _create_step_meta(self) -> Dict[str, Any]:
        """Create step metadata."""
        now = datetime.now(timezone.utc)
        return {
            "step_id": self.agent_id,
            "agent_name": self.agent_name,
            "run_id": getattr(self, 'run_id', 'unknown'),
            "started_at_utc": now.isoformat(),
            "finished_at_utc": now.isoformat(),
            "pipeline_version": "1.0.0"
        }


# NOTE: Wiring-safe alias for dynamic loaders expecting `Agent` symbol in this module.
Agent = AG15NetworkMapper