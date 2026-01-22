"""
AG-15 Network Mapper Agent

Responsible for expanding the lead universe by identifying related companies
based on the Intake Company's business segment and customer base.
"""

from datetime import datetime, timezone
from typing import Dict, Any, Optional, List
from urllib.parse import quote_plus

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

        # Core industries with DE/EN synonyms (used to broaden search intent)
        self.core_industries = {
            "medical_technology": [
                "Medizintechnik",
                "MedTech",
                "medical technology",
                "medical devices",
            ],
            "mechanical_engineering": [
                "Maschinenbau",
                "mechanical engineering",
                "industrial machinery",
                "machine building",
            ],
            "electrical_engineering": [
                "Elektrotechnik",
                "electrical engineering",
                "industrial electronics",
                "automation technology",
            ],
        }

    def run(
        self,
        case_input: Dict[str, Any],
        meta_case_normalized: Dict[str, Any],
        meta_target_entity_stub: Dict[str, Any],
        registry_snapshot: Optional[Dict[str, Any]] = None,
    ) -> AgentResult:
        """
        Execute network mapping for the target company.
        """
        company_name = str(meta_case_normalized.get("company_name_canonical", "")).strip()
        domain = str(meta_case_normalized.get("web_domain_normalized", "")).strip()

        output = {
            "step_meta": self._create_step_meta(),
            "entities_delta": [],
            "relations_delta": [],
            "findings": [],
            "sources": [],
        }

        try:
            network_data = self._research_network_connections(
                company_name, domain, meta_target_entity_stub
            )

            if network_data:
                # Convert entities dict to array format
                entities_list = []
                for entity_id, entity_data in network_data["entities"].items():
                    entity_data["entity_id"] = entity_id
                    entities_list.append(entity_data)
                
                # Convert relations dict to array format  
                relations_list = list(network_data["relations"].values())
                
                output["entities_delta"] = entities_list
                output["relations_delta"] = relations_list
                output["findings"] = [network_data["findings"]]
                output["sources"] = network_data["sources"]

        except Exception as e:
            self.logger.error(f"Error in AG-15 execution: {str(e)}")
            output["findings"] = [{"error": f"Network mapping failed: {str(e)}", "network_expansion_summary": "Error occurred"}]
        
        # Ensure required fields for contract validation
        if not output["findings"]:
            output["findings"] = [{"network_expansion_summary": "Network mapping completed"}]

        return AgentResult(ok=True, output=output)

    def _build_search_queries(self, company_name: str) -> List[str]:
        """
        Build ordered, de-duplicated search queries for network discovery.
        Includes both general and industry-scoped queries (DE+EN synonyms).
        """
        company_name = (company_name or "").strip()
        if not company_name:
            return []

        base_templates = [
            "{c} competitors same industry",
            "{c} suppliers customers business partners",
            "{c} supply chain network",
            "{c} business relationships",
            "{c} key customers",
            "{c} key suppliers",
        ]

        industry_templates = [
            "{c} competitors {i}",
            "{c} competitors in {i}",
            "{c} alternatives {i}",
            "{c} peer companies {i}",
            "{c} industry peers {i}",
            "{c} suppliers {i}",
            "{c} customers {i}",
            "{c} business partners {i}",
            "{c} distribution partners {i}",
            "{c} supply chain {i}",
            "{c} value chain {i}",
            "{c} strategic partners {i}",
        ]

        seen = set()
        queries: List[str] = []

        def _add(q: str) -> None:
            qn = " ".join((q or "").split()).strip()
            if qn and qn not in seen:
                seen.add(qn)
                queries.append(qn)

        # General queries first (stable order)
        for t in base_templates:
            _add(t.format(c=company_name))

        # Industry-scoped queries (stable order: dict insertion + synonym order)
        for _, synonyms in self.core_industries.items():
            for ind in synonyms:
                for t in industry_templates:
                    _add(t.format(c=company_name, i=ind))

        return queries

    def _research_network_connections(
        self, company_name: str, domain: str, target_entity: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        Research network connections for the target company using OpenAI.
        """
        import os
        import httpx
        import json
        
        api_key = os.getenv("OPEN-AI-KEY") or os.getenv("OPENAI_API_KEY")
        if not api_key:
            return self._fallback_network_data(company_name)
        
        # Build comprehensive search context
        search_context = f"""
Company: {company_name}
Domain: {domain}
Industries: Medical Technology, Mechanical Engineering, Electrical Engineering

Find real competitors, suppliers, customers, and business partners for this company.
Focus on companies in the same or related industries.
"""
        
        try:
            payload = {
                "model": "gpt-4o-mini",
                "messages": [
                    {
                        "role": "system",
                        "content": "You are a business intelligence researcher. Find real companies that are competitors, suppliers, customers, or partners of the given company. Return JSON with 'peers' and 'customers' arrays. Each entry needs: entity_name, industry, rationale. Use real company names only."
                    },
                    {
                        "role": "user", 
                        "content": search_context
                    }
                ],
                "temperature": 0.3,
                "max_tokens": 1000
            }
            
            headers = {"Authorization": f"Bearer {api_key}"}
            with httpx.Client(timeout=30.0) as client:
                resp = client.post("https://api.openai.com/v1/chat/completions", json=payload, headers=headers)
                resp.raise_for_status()
                data = resp.json()
            
            content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
            if content:
                try:
                    research_data = json.loads(content)
                    return self._process_openai_results(research_data, company_name)
                except json.JSONDecodeError:
                    pass
                    
        except Exception as e:
            self.logger.error(f"OpenAI research failed: {str(e)}")
        
        return self._fallback_network_data(company_name)

    def _process_openai_results(self, research_data: Dict[str, Any], company_name: str) -> Dict[str, Any]:
        """Process OpenAI research results into entities and relations."""
        entities_delta = {}
        accessed_at = datetime.now(timezone.utc).isoformat()
        
        # Process peers
        peers = research_data.get("peers", [])
        for i, peer in enumerate(peers[:3]):  # Limit to 3
            entity_id = f"PEER-{i+1:03d}"
            entities_delta[entity_id] = {
                "entity_key": f"peer-{i+1:03d}",
                "entity_name": peer.get("entity_name", "Unknown"),
                "industry": peer.get("industry", "n/v"),
                "relationship_type": "peer",
                "rationale": peer.get("rationale", "Identified as industry peer")
            }
        
        # Process customers
        customers = research_data.get("customers", [])
        for i, customer in enumerate(customers[:3]):  # Limit to 3
            entity_id = f"CUSTOMER-{i+1:03d}"
            entities_delta[entity_id] = {
                "entity_key": f"customer-{i+1:03d}",
                "entity_name": customer.get("entity_name", "Unknown"),
                "industry": customer.get("industry", "n/v"),
                "relationship_type": "customer",
                "rationale": customer.get("rationale", "Identified as potential customer")
            }
        
        relations_delta = self._build_relations("", entities_delta)
        
        sources = [{
            "publisher": "OpenAI Research",
            "url": "https://api.openai.com/v1/chat/completions",
            "title": f"AI-powered network research for {company_name}",
            "accessed_at_utc": accessed_at
        }]
        
        findings = {
            "network_expansion_summary": f"AI research identified {len(entities_delta)} related companies for {company_name}",
            "peer_count": len([e for e in entities_delta.values() if e.get("relationship_type") == "peer"]),
            "customer_count": len([e for e in entities_delta.values() if e.get("relationship_type") == "customer"]),
        }
        
        return {
            "entities": entities_delta,
            "relations": relations_delta,
            "findings": findings,
            "sources": sources
        }
    
    def _fallback_network_data(self, company_name: str) -> Dict[str, Any]:
        """Fallback when OpenAI is not available."""
        entities_delta = {
            "PEER-001": {
                "entity_key": "peer-fallback-001",
                "entity_name": "Industry Peer (Fallback)",
                "industry": "n/v",
                "relationship_type": "peer",
                "rationale": "Fallback data - OpenAI unavailable"
            }
        }
        
        relations_delta = self._build_relations("", entities_delta)
        
        sources = [{
            "publisher": "Fallback Data",
            "url": "n/v",
            "title": f"Fallback network data for {company_name}",
            "accessed_at_utc": datetime.now(timezone.utc).isoformat()
        }]
        
        findings = {
            "network_expansion_summary": f"Fallback: Limited network data for {company_name}",
            "peer_count": 1,
            "customer_count": 0,
        }
        
        return {
            "entities": entities_delta,
            "relations": relations_delta,
            "findings": findings,
            "sources": sources
        }

    def _build_relations(self, source_entity_key: str, discovered_entities: Dict[str, Any]) -> Dict[str, Any]:
        """Build relations delta from discovered entities."""
        relations: Dict[str, Any] = {}

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
                "rationale": entity_data.get("rationale", "n/v"),
            }

        return relations

    def _create_step_meta(self) -> Dict[str, Any]:
        now = datetime.now(timezone.utc)
        return {
            "step_id": self.agent_id,
            "agent_name": self.agent_name,
            "run_id": getattr(self, "run_id", "unknown"),
            "started_at_utc": now.isoformat(),
            "finished_at_utc": now.isoformat(),
            "pipeline_version": "1.0.0",
        }


# Wiring-safe alias for dynamic loaders expecting `Agent` symbol in this module.
Agent = AG15NetworkMapper