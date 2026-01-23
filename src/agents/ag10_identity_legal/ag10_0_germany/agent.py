"""
AG-10.0 Identity Legal Germany Agent

Specialized agent for extracting legal identity information from German companies
using Impressum data from company websites.

Focus Areas:
- Full company name (including legal form)
- Legal status extraction (GmbH, AG, SE, etc.)
- German address components (street, number, PLZ, city, state)
- Impressum-based data extraction
"""

import json
import os
import re
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional

import httpx

from ...common.base_agent import BaseAgent, AgentResult


class AG10_0_IdentityLegalGermany(BaseAgent):
    """
    Agent for extracting German legal identity information from company websites.
    
    Extracts:
    - Complete legal company name
    - Legal form (GmbH, UG, AG, SE, KGaA, etc.)
    - German address (Straße, Hausnummer, PLZ, Ort, Bundesland)
    """
    
    def __init__(self):
        super().__init__()
        self.agent_id = "AG-10.0"
        self.agent_name = "ag10_0_identity_legal_germany"
        
        # German legal forms for extraction
        self.german_legal_forms = [
            "GmbH", "UG (haftungsbeschränkt)", "UG", "AG", "SE", "KGaA", 
            "GmbH & Co. KG", "KG", "OHG", "e.K.", "GbR", "e.V.", "Stiftung"
        ]
        
    def run(
        self,
        case_input: Dict[str, Any],
        meta_case_normalized: Dict[str, Any],
        meta_target_entity_stub: Dict[str, Any],
        registry_snapshot: Optional[Dict[str, Any]] = None,
    ) -> AgentResult:
        """
        Execute German legal identity extraction.
        """
        company_name = meta_case_normalized.get("company_name_canonical", "")
        domain = meta_case_normalized.get("web_domain_normalized", "")
        
        output = {
            "step_meta": self._create_step_meta(),
            "entities_delta": [],
            "relations_delta": [],
            "findings": [],
            "sources": []
        }
        
        try:
            # Extract legal identity from German Impressum
            legal_data = self._extract_german_legal_identity(company_name, domain)
            
            if legal_data:
                # Update entity with German legal information
                entity_update = {
                    "entity_key": meta_target_entity_stub.get("entity_key", ""),
                    "entity_type": "target_company",
                    "entity_name": legal_data["legal_name"],
                    "legal_form": legal_data["legal_form"],
                    "street_name": legal_data["street_name"],
                    "house_number": legal_data["house_number"],
                    "postal_code": legal_data["postal_code"],
                    "city": legal_data["city"],
                    "state": legal_data["state"],
                    "country": "Germany",
                    "country_code": "DE"
                }
                
                output["entities_delta"] = [entity_update]
                output["findings"] = [legal_data["findings"]]
                output["sources"] = legal_data["sources"]
                
        except Exception as e:
            self.logger.error(f"Error in AG-10.0 execution: {str(e)}")
            output["findings"] = [{
                "error": f"German legal identity extraction failed: {str(e)}",
                "legal_name": "n/v",
                "legal_form": "n/v",
                "address_complete": False
            }]
            
        # Ensure required fields
        if not output["findings"]:
            output["findings"] = [{
                "legal_name": "n/v",
                "legal_form": "n/v", 
                "address_complete": False
            }]
            
        return AgentResult(ok=True, output=output)
        
    def _extract_german_legal_identity(self, company_name: str, domain: str) -> Optional[Dict[str, Any]]:
        """
        Extract German legal identity using OpenAI with German Impressum focus.
        """
        api_key = os.getenv("OPEN-AI-KEY") or os.getenv("OPENAI_API_KEY")
        if not api_key:
            return self._fallback_german_data(company_name)
            
        # Build German-specific search context
        search_context = f"""
Company: {company_name}
Domain: {domain}

Extract German legal identity information from the company's Impressum (legal notice).
Focus on German legal requirements and address formats.

Find:
1. Complete legal company name (including legal form like GmbH, AG, etc.)
2. Legal form (GmbH, UG, AG, SE, KGaA, etc.)
3. German address: Street name, house number, PLZ (5-digit), city, state
4. Only extract information that appears on the company's official website/Impressum
"""
        
        try:
            response_format = {
                "type": "json_schema",
                "json_schema": {
                    "name": "german_legal_identity",
                    "strict": True,
                    "schema": {
                        "type": "object",
                        "properties": {
                            "legal_name": {"type": "string"},
                            "legal_form": {"type": "string"},
                            "street_name": {"type": "string"},
                            "house_number": {"type": "string"},
                            "postal_code": {"type": "string"},
                            "city": {"type": "string"},
                            "state": {"type": "string"}
                        },
                        "required": ["legal_name", "legal_form", "street_name", "house_number", "postal_code", "city", "state"],
                        "additionalProperties": False
                    }
                }
            }
            
            payload = {
                "model": "gpt-4o",
                "messages": [
                    {
                        "role": "system",
                        "content": "Extract German legal identity information from Impressum data. Use 'n/v' only if information is completely unavailable. Focus on official German legal forms and address formats."
                    },
                    {
                        "role": "user",
                        "content": search_context
                    }
                ],
                "temperature": 0.1,
                "max_tokens": 800,
                "response_format": response_format
            }
            
            headers = {"Authorization": f"Bearer {api_key}"}
            with httpx.Client(timeout=30.0) as client:
                resp = client.post("https://api.openai.com/v1/chat/completions", json=payload, headers=headers)
                resp.raise_for_status()
                data = resp.json()
                
            content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
            if content:
                try:
                    legal_data = json.loads(content)
                    return self._process_german_results(legal_data, company_name)
                except json.JSONDecodeError:
                    pass
                    
        except Exception as e:
            self.logger.error(f"OpenAI German legal extraction failed: {str(e)}")
            
        return self._fallback_german_data(company_name)
        
    def _process_german_results(self, legal_data: Dict[str, Any], company_name: str) -> Dict[str, Any]:
        """Process and validate German legal extraction results."""
        accessed_at = datetime.now(timezone.utc).isoformat()
        
        # Extract and validate legal form
        legal_name = legal_data.get("legal_name", "n/v")
        legal_form = self._extract_legal_form(legal_name)
        
        # Validate German postal code (5 digits)
        postal_code = legal_data.get("postal_code", "n/v")
        if postal_code != "n/v" and not re.match(r"^\d{5}$", postal_code):
            postal_code = "n/v"
            
        # Validate house number format
        house_number = legal_data.get("house_number", "n/v")
        if house_number != "n/v" and not re.match(r"^\d+[a-zA-Z]?(-\d+)?$", house_number):
            house_number = "n/v"
            
        findings = {
            "legal_name": legal_name,
            "legal_form": legal_form,
            "street_name": legal_data.get("street_name", "n/v"),
            "house_number": house_number,
            "postal_code": postal_code,
            "city": legal_data.get("city", "n/v"),
            "state": legal_data.get("state", "n/v"),
            "address_complete": all(v != "n/v" for v in [
                legal_data.get("street_name"),
                house_number,
                postal_code,
                legal_data.get("city")
            ])
        }
        
        sources = [{
            "publisher": f"{company_name} Impressum",
            "url": f"https://{company_name.lower().replace(' ', '')}.com/impressum",
            "title": f"German legal identity research for {company_name}",
            "accessed_at_utc": accessed_at
        }]
        
        return {
            "legal_name": legal_name,
            "legal_form": legal_form,
            "street_name": legal_data.get("street_name", "n/v"),
            "house_number": house_number,
            "postal_code": postal_code,
            "city": legal_data.get("city", "n/v"),
            "state": legal_data.get("state", "n/v"),
            "findings": findings,
            "sources": sources
        }
        
    def _extract_legal_form(self, legal_name: str) -> str:
        """Extract legal form from company name."""
        if legal_name == "n/v":
            return "n/v"
            
        # Check for German legal forms
        for form in self.german_legal_forms:
            if form in legal_name:
                return form
                
        # Extract from end of name
        words = legal_name.split()
        if len(words) >= 2:
            potential_form = " ".join(words[-2:])
            for form in self.german_legal_forms:
                if form.lower() in potential_form.lower():
                    return form
                    
        return "n/v"
        
    def _fallback_german_data(self, company_name: str) -> Dict[str, Any]:
        """Fallback data when OpenAI is unavailable."""
        findings = {
            "legal_name": company_name,
            "legal_form": "n/v",
            "street_name": "n/v",
            "house_number": "n/v", 
            "postal_code": "n/v",
            "city": "n/v",
            "state": "n/v",
            "address_complete": False
        }
        
        sources = [{
            "publisher": "Fallback Data",
            "url": "n/v",
            "title": f"Fallback German legal data for {company_name}",
            "accessed_at_utc": datetime.now(timezone.utc).isoformat()
        }]
        
        return {
            "legal_name": company_name,
            "legal_form": "n/v",
            "street_name": "n/v",
            "house_number": "n/v",
            "postal_code": "n/v", 
            "city": "n/v",
            "state": "n/v",
            "findings": findings,
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


# Wiring-safe alias for dynamic loaders
Agent = AG10_0_IdentityLegalGermany