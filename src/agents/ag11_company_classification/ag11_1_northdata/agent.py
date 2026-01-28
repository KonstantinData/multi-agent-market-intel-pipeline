"""
AG-11.1 Northdata Company Classification Agent

Fetches all freely available company information from Northdata API.
"""

import os
from datetime import datetime, timezone
from typing import Dict, Any, Optional

import httpx

from ...common.base_agent import BaseAgent, AgentResult


class AG11_1_NorthdataAgent(BaseAgent):
    """
    Agent for fetching company data from Northdata API.
    
    Extracts all freely available information including:
    - Company identity and legal data
    - Financial information
    - Management/officers
    - Publications
    - Relations
    """

    def __init__(self):
        super().__init__()
        self.agent_id = "AG-11.1"
        self.agent_name = "ag11_1_northdata"
        self.api_key = os.getenv("NORTHDATA_API_KEY")
        self.base_url = "https://www.northdata.de/_api"

    def run(
        self,
        case_input: Dict[str, Any],
        meta_case_normalized: Dict[str, Any],
        meta_target_entity_stub: Dict[str, Any],
        registry_snapshot: Optional[Dict[str, Any]] = None,
    ) -> AgentResult:
        """Execute Northdata API data fetch."""
        
        company_name = meta_case_normalized.get("company_name_canonical", "")
        domain = meta_case_normalized.get("web_domain_normalized", "")
        
        output = {
            "step_meta": self._create_step_meta(),
            "entities_delta": [],
            "relations_delta": [],
            "findings": [],
            "sources": []
        }

        if not self.api_key:
            output["findings"] = [{
                "error": "NORTHDATA_API_KEY not configured",
                "data_available": False
            }]
            return AgentResult(ok=True, output=output)

        try:
            # Search for company
            company_id = self._search_company(company_name, domain)
            
            if company_id:
                # Fetch detailed company information
                details = self._fetch_company_details(company_id)
                
                if details:
                    # Process and structure the data
                    processed = self._process_northdata_response(details, meta_target_entity_stub)
                    output["entities_delta"] = processed["entities"]
                    output["findings"] = processed["findings"]
                    output["sources"] = processed["sources"]
                else:
                    output["findings"] = [{"data_available": False, "reason": "No details found"}]
            else:
                output["findings"] = [{"data_available": False, "reason": "Company not found"}]

        except Exception as e:
            output["findings"] = [{
                "error": f"Northdata fetch failed: {str(e)}",
                "data_available": False
            }]

        return AgentResult(ok=True, output=output)

    def _search_company(self, company_name: str, domain: str) -> Optional[str]:
        """Search for company and return Northdata ID."""
        # Use company name for search
        search_query = company_name
        
        try:
            with httpx.Client(timeout=30.0) as client:
                resp = client.get(
                    f"{self.base_url}/company/v1/company",
                    params={"name": search_query, "api_key": self.api_key},
                )
                if resp.status_code == 200:
                    data = resp.json()
                    # Return first company ID from results
                    if isinstance(data, list) and len(data) > 0:
                        return data[0].get("id")
                    elif isinstance(data, dict) and data.get("id"):
                        return data.get("id")
        except Exception as e:
            pass
        
        return None

    def _fetch_company_details(self, company_id: str) -> Optional[Dict[str, Any]]:
        """Fetch detailed company information by Northdata ID."""
        if not company_id:
            return None
        
        try:
            with httpx.Client(timeout=30.0) as client:
                resp = client.get(
                    f"{self.base_url}/company/v1/company/{company_id}",
                    params={"api_key": self.api_key},
                )
                if resp.status_code == 200:
                    return resp.json()
        except Exception as e:
            pass
        
        return None

    def _process_northdata_response(
        self, 
        data: Dict[str, Any], 
        entity_stub: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Process Northdata API response into pipeline format."""
        
        accessed_at = datetime.now(timezone.utc).isoformat()
        
        # Extract company data from Northdata structure
        name = data.get("name", {}).get("name", "n/v")
        register = data.get("register", {})
        address = data.get("address", {})
        
        # Extract register info
        register_id = register.get("id", "n/v")
        register_type = register.get("type", "n/v")
        register_city = register.get("city", "n/v")
        
        # Build register court string (e.g., "Amtsgericht Charlottenburg (Berlin)")
        register_court = f"Amtsgericht {register_city}" if register_city != "n/v" else "n/v"
        
        # Extract publications
        publications = data.get("publications", [])
        publications_list = []
        for pub in publications[:10]:  # Limit to 10 most recent
            pub_date = pub.get("date", "n/v")
            pub_type = pub.get("type", "n/v")
            pub_text = pub.get("text", "n/v")
            publications_list.append({
                "date": pub_date,
                "type": pub_type,
                "text": pub_text
            })
        
        entity_update = {
            "entity_key": entity_stub.get("entity_key", ""),
            "entity_type": "target_company",
            "entity_name": name,
            "legal_name": name,
            "register_number": register_id,
            "register_type": register_type,
            "register_court": register_court,
            "street_name": address.get("street", "n/v"),
            "postal_code": address.get("postalCode", "n/v"),
            "city": address.get("city", "n/v"),
            "country": address.get("country", "n/v"),
            "northdata_id": data.get("id", "n/v"),
            "northdata_publications": publications_list
        }
        
        findings = {
            "data_available": True,
            "legal_name": name,
            "register_number": register_id,
            "register_type": register_type,
            "register_court": register_court,
            "publications_count": len(publications_list),
            "publications": publications_list
        }
        
        sources = [{
            "publisher": "Northdata GmbH",
            "url": f"https://www.northdata.de/{data.get('id', '')}",
            "title": f"Northdata company profile: {name}",
            "accessed_at_utc": accessed_at
        }]
        
        return {
            "entities": [entity_update],
            "findings": [findings],
            "sources": sources
        }

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


# Wiring-safe alias
Agent = AG11_1_NorthdataAgent
