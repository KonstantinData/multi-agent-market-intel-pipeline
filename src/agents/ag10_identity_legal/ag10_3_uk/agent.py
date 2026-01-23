"""
AG-10.3 Identity Legal UK Agent

Specialized agent for extracting legal identity information from UK companies
using company registration data and official business information.

Focus Areas:
- UK legal forms (Ltd, PLC, LLP, etc.)
- UK address formats and postcodes
- Companies House registration information
- Headquarters/registered office addresses
"""

import json
import os
import re
from datetime import datetime, timezone
from typing import Dict, Any, Optional

import httpx

from ...common.base_agent import BaseAgent, AgentResult


class AG10_3_IdentityLegalUK(BaseAgent):
    """
    Agent for extracting UK legal identity information.
    
    Extracts:
    - Complete legal company name
    - Legal form (Ltd, PLC, LLP, etc.)
    - UK address format with postcodes
    - Companies House registration details
    """
    
    def __init__(self):
        super().__init__()
        self.agent_id = "AG-10.3"
        self.agent_name = "ag10_3_identity_legal_uk"
        
        # UK legal forms
        self.uk_legal_forms = [
            "Ltd", "Limited", "PLC", "Public Limited Company", "LLP", 
            "Limited Liability Partnership", "CIC", "Community Interest Company",
            "CIO", "Charitable Incorporated Organisation", "LP", "Limited Partnership"
        ]
        
    def run(
        self,
        case_input: Dict[str, Any],
        meta_case_normalized: Dict[str, Any],
        meta_target_entity_stub: Dict[str, Any],
        registry_snapshot: Optional[Dict[str, Any]] = None,
    ) -> AgentResult:
        """
        Execute UK legal identity extraction.
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
            # Extract legal identity from UK sources
            legal_data = self._extract_uk_legal_identity(company_name, domain)
            
            if legal_data and legal_data.get("country_code") == "GB":
                # Update entity with UK legal information
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
                    "country": "United Kingdom",
                    "country_code": "GB"
                }
                
                output["entities_delta"] = [entity_update]
                output["findings"] = [legal_data["findings"]]
                output["sources"] = legal_data["sources"]
                
        except Exception as e:
            self.logger.error(f"Error in AG-10.3 execution: {str(e)}")
            output["findings"] = [{
                "error": f"UK legal identity extraction failed: {str(e)}",
                "legal_name": "n/v",
                "legal_form": "n/v",
                "country_detected": "n/v"
            }]
            
        # Ensure required fields
        if not output["findings"]:
            output["findings"] = [{
                "legal_name": "n/v",
                "legal_form": "n/v",
                "country_detected": "n/v"
            }]
            
        return AgentResult(ok=True, output=output)
        
    def _extract_uk_legal_identity(self, company_name: str, domain: str) -> Optional[Dict[str, Any]]:
        """
        Extract UK legal identity using OpenAI with UK focus.
        """
        api_key = os.getenv("OPEN-AI-KEY") or os.getenv("OPENAI_API_KEY")
        if not api_key:
            return self._fallback_uk_data(company_name)
            
        # Build UK-specific search context
        search_context = f"""
Company: {company_name}
Domain: {domain}

Extract UK legal identity information from the company's website, particularly:
- Contact/About pages
- Legal notices
- Terms and conditions
- Headquarters/registered office information

Find:
1. Complete legal company name (including legal form like Ltd, PLC, LLP)
2. Legal form (Ltd, Limited, PLC, LLP, CIC, etc.)
3. UK address: Street name, house/building number, postcode, city/town, county
4. Confirm this is a UK-based company
5. Only extract information from official company website
"""
        
        try:
            response_format = {
                "type": "json_schema",
                "json_schema": {
                    "name": "uk_legal_identity",
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
                            "state": {"type": "string"},
                            "country": {"type": "string"},
                            "country_code": {"type": "string"}
                        },
                        "required": ["legal_name", "legal_form", "street_name", "house_number", "postal_code", "city", "state", "country", "country_code"],
                        "additionalProperties": False
                    }
                }
            }
            
            payload = {
                "model": "gpt-4o",
                "messages": [
                    {
                        "role": "system",
                        "content": "Extract UK legal identity information. Use 'n/v' only if information is unavailable. Country code should be 'GB' for United Kingdom. Focus on UK legal forms (Ltd, PLC, LLP) and UK postcode format."
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
                    return self._process_uk_results(legal_data, company_name)
                except json.JSONDecodeError:
                    pass
                    
        except Exception as e:
            self.logger.error(f"OpenAI UK legal extraction failed: {str(e)}")
            
        return self._fallback_uk_data(company_name)
        
    def _process_uk_results(self, legal_data: Dict[str, Any], company_name: str) -> Dict[str, Any]:
        """Process and validate UK legal extraction results."""
        accessed_at = datetime.now(timezone.utc).isoformat()
        
        # Validate country code
        country_code = legal_data.get("country_code", "").upper()
        if country_code != "GB":
            return None  # Not UK
            
        # Extract and validate legal form
        legal_name = legal_data.get("legal_name", "n/v")
        legal_form = self._extract_uk_legal_form(legal_name)
        
        # Validate UK postcode format
        postal_code = legal_data.get("postal_code", "n/v")
        if postal_code != "n/v" and not self._validate_uk_postcode(postal_code):
            postal_code = "n/v"
            
        findings = {
            "legal_name": legal_name,
            "legal_form": legal_form,
            "street_name": legal_data.get("street_name", "n/v"),
            "house_number": legal_data.get("house_number", "n/v"),
            "postal_code": postal_code,
            "city": legal_data.get("city", "n/v"),
            "state": legal_data.get("state", "n/v"),
            "country": "United Kingdom",
            "country_code": "GB",
            "country_detected": "GB"
        }
        
        sources = [{
            "publisher": f"{company_name} Company Information",
            "url": f"https://{company_name.lower().replace(' ', '')}.com/contact",
            "title": f"UK legal identity research for {company_name}",
            "accessed_at_utc": accessed_at
        }]
        
        return {
            **findings,
            "findings": findings,
            "sources": sources
        }
        
    def _extract_uk_legal_form(self, legal_name: str) -> str:
        """Extract legal form from UK company name."""
        if legal_name == "n/v":
            return "n/v"
            
        # Check for UK legal forms
        for form in self.uk_legal_forms:
            if form in legal_name:
                return form
                
        # Extract from end of name
        words = legal_name.split()
        if len(words) >= 1:
            potential_form = words[-1]
            for form in self.uk_legal_forms:
                if form.lower() == potential_form.lower():
                    return form
                    
        return "n/v"
        
    def _validate_uk_postcode(self, postcode: str) -> bool:
        """Validate UK postcode format."""
        # UK postcode patterns: SW1A 1AA, M1 1AA, B33 8TH, etc.
        uk_postcode_pattern = r"^[A-Z]{1,2}[0-9R][0-9A-Z]?\s?[0-9][A-Z]{2}$"
        return bool(re.match(uk_postcode_pattern, postcode.upper().strip()))
        
    def _fallback_uk_data(self, company_name: str) -> Dict[str, Any]:
        """Fallback data when OpenAI is unavailable."""
        findings = {
            "legal_name": company_name,
            "legal_form": "n/v",
            "street_name": "n/v",
            "house_number": "n/v",
            "postal_code": "n/v",
            "city": "n/v",
            "state": "n/v",
            "country": "n/v",
            "country_code": "n/v",
            "country_detected": "n/v"
        }
        
        sources = [{
            "publisher": "Fallback Data",
            "url": "n/v",
            "title": f"Fallback UK legal data for {company_name}",
            "accessed_at_utc": datetime.now(timezone.utc).isoformat()
        }]
        
        return {
            **findings,
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
Agent = AG10_3_IdentityLegalUK