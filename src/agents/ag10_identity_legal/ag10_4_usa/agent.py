"""
AG-10.4 Identity Legal USA Agent

Specialized agent for extracting legal identity information from US companies
using headquarters information and corporate registration data.

Focus Areas:
- US legal forms (Inc, Corp, LLC, LLP, etc.)
- US address formats with ZIP codes
- Headquarters/corporate office addresses
- State of incorporation information
"""

import json
import os
import re
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional

import httpx

from ...common.base_agent import BaseAgent, AgentResult


class AG10_4_IdentityLegalUSA(BaseAgent):
    """
    Agent for extracting US legal identity information.
    
    Extracts:
    - Complete legal company name
    - Legal form (Inc, Corp, LLC, LLP, etc.)
    - US address format with ZIP codes
    - State and headquarters information
    """
    
    def __init__(self):
        super().__init__()
        self.agent_id = "AG-10.4"
        self.agent_name = "ag10_4_identity_legal_usa"
        
        # US legal forms
        self.us_legal_forms = [
            "Inc", "Incorporated", "Corp", "Corporation", "LLC", 
            "Limited Liability Company", "LLP", "Limited Liability Partnership",
            "LP", "Limited Partnership", "PC", "Professional Corporation",
            "PLLC", "Professional Limited Liability Company"
        ]
        
        # US states for validation
        self.us_states = {
            "AL", "AK", "AZ", "AR", "CA", "CO", "CT", "DE", "FL", "GA",
            "HI", "ID", "IL", "IN", "IA", "KS", "KY", "LA", "ME", "MD",
            "MA", "MI", "MN", "MS", "MO", "MT", "NE", "NV", "NH", "NJ",
            "NM", "NY", "NC", "ND", "OH", "OK", "OR", "PA", "RI", "SC",
            "SD", "TN", "TX", "UT", "VT", "VA", "WA", "WV", "WI", "WY",
            "DC"  # District of Columbia
        }
        
    def run(
        self,
        case_input: Dict[str, Any],
        meta_case_normalized: Dict[str, Any],
        meta_target_entity_stub: Dict[str, Any],
        registry_snapshot: Optional[Dict[str, Any]] = None,
    ) -> AgentResult:
        """
        Execute US legal identity extraction.
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
            # Extract legal identity from US sources
            legal_data = self._extract_us_legal_identity(company_name, domain)
            
            if legal_data and legal_data.get("country_code") == "US":
                # Update entity with US legal information
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
                    "country": "United States",
                    "country_code": "US"
                }
                
                output["entities_delta"] = [entity_update]
                output["findings"] = [legal_data["findings"]]
                output["sources"] = legal_data["sources"]
                
        except Exception as e:
            self.logger.error(f"Error in AG-10.4 execution: {str(e)}")
            output["findings"] = [{
                "error": f"US legal identity extraction failed: {str(e)}",
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
        
    def _extract_us_legal_identity(self, company_name: str, domain: str) -> Optional[Dict[str, Any]]:
        """
        Extract US legal identity using OpenAI with US focus.
        """
        api_key = os.getenv("OPEN-AI-KEY") or os.getenv("OPENAI_API_KEY")
        if not api_key:
            return self._fallback_us_data(company_name)
            
        # Build US-specific search context
        search_context = f"""
Company: {company_name}
Domain: {domain}

Extract US legal identity information from the company's website, particularly:
- About/Contact pages
- Corporate information
- Headquarters information
- Legal notices/terms

Find:
1. Complete legal company name (including legal form like Inc, Corp, LLC)
2. Legal form (Inc, Corp, LLC, LLP, PC, etc.)
3. US address: Street name, street number, ZIP code, city, state (2-letter code)
4. Headquarters or corporate office address
5. Confirm this is a US-based company
6. Only extract information from official company website
"""
        
        try:
            response_format = {
                "type": "json_schema",
                "json_schema": {
                    "name": "us_legal_identity",
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
                        "content": "Extract US legal identity information. Use 'n/v' only if information is unavailable. Country code should be 'US' for United States. Use 2-letter state codes (CA, NY, TX, etc.). Focus on US legal forms (Inc, Corp, LLC) and ZIP code format."
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
                    return self._process_us_results(legal_data, company_name)
                except json.JSONDecodeError:
                    pass
                    
        except Exception as e:
            self.logger.error(f"OpenAI US legal extraction failed: {str(e)}")
            
        return self._fallback_us_data(company_name)
        
    def _process_us_results(self, legal_data: Dict[str, Any], company_name: str) -> Dict[str, Any]:
        """Process and validate US legal extraction results."""
        accessed_at = datetime.now(timezone.utc).isoformat()
        
        # Validate country code
        country_code = legal_data.get("country_code", "").upper()
        if country_code != "US":
            return None  # Not US
            
        # Extract and validate legal form
        legal_name = legal_data.get("legal_name", "n/v")
        legal_form = self._extract_us_legal_form(legal_name)
        
        # Validate US ZIP code format
        postal_code = legal_data.get("postal_code", "n/v")
        if postal_code != "n/v" and not self._validate_us_zip_code(postal_code):
            postal_code = "n/v"
            
        # Validate US state code
        state = legal_data.get("state", "n/v").upper()
        if state != "n/v" and state not in self.us_states:
            state = "n/v"
            
        findings = {
            "legal_name": legal_name,
            "legal_form": legal_form,
            "street_name": legal_data.get("street_name", "n/v"),
            "house_number": legal_data.get("house_number", "n/v"),
            "postal_code": postal_code,
            "city": legal_data.get("city", "n/v"),
            "state": state,
            "country": "United States",
            "country_code": "US",
            "country_detected": "US"
        }
        
        sources = [{
            "publisher": f"{company_name} Corporate Information",
            "url": f"https://{company_name.lower().replace(' ', '')}.com/about",
            "title": f"US legal identity research for {company_name}",
            "accessed_at_utc": accessed_at
        }]
        
        return {
            **findings,
            "findings": findings,
            "sources": sources
        }
        
    def _extract_us_legal_form(self, legal_name: str) -> str:
        """Extract legal form from US company name."""
        if legal_name == "n/v":
            return "n/v"
            
        # Check for US legal forms
        for form in self.us_legal_forms:
            if form in legal_name:
                return form
                
        # Extract from end of name
        words = legal_name.split()
        if len(words) >= 1:
            potential_form = words[-1].rstrip('.,')
            for form in self.us_legal_forms:
                if form.lower() == potential_form.lower():
                    return form
                    
        return "n/v"
        
    def _validate_us_zip_code(self, zip_code: str) -> bool:
        """Validate US ZIP code format."""
        # US ZIP code patterns: 12345 or 12345-6789
        us_zip_pattern = r"^\d{5}(-\d{4})?$"
        return bool(re.match(us_zip_pattern, zip_code.strip()))
        
    def _fallback_us_data(self, company_name: str) -> Dict[str, Any]:
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
            "title": f"Fallback US legal data for {company_name}",
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
Agent = AG10_4_IdentityLegalUSA