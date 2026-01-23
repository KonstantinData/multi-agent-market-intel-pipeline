"""
AG-10.1 Identity Legal DACH Agent

Specialized agent for extracting legal identity information from Austrian and Swiss companies
using Impressum data from company websites.

Focus Areas:
- Austrian legal forms (GmbH, AG, e.U., OG, KG, etc.)
- Swiss legal forms (AG, GmbH, Einzelfirma, etc.)
- DACH address formats and postal codes
- Multi-language support (German)
"""

import json
import os
import re
from datetime import datetime, timezone
from typing import Dict, Any, Optional

import httpx

from ...common.base_agent import BaseAgent, AgentResult


class AG10_1_IdentityLegalDACH(BaseAgent):
    """
    Agent for extracting Austrian and Swiss legal identity information.
    
    Extracts:
    - Complete legal company name
    - Legal form (AT: GmbH, AG, e.U., OG, KG / CH: AG, GmbH, etc.)
    - DACH address formats (AT: 4-digit PLZ / CH: 4-digit PLZ)
    """
    
    def __init__(self):
        super().__init__()
        self.agent_id = "AG-10.1"
        self.agent_name = "ag10_1_identity_legal_dach"
        
        # Austrian legal forms
        self.austrian_legal_forms = [
            "GmbH", "AG", "e.U.", "OG", "KG", "GmbH & Co KG", 
            "Genossenschaft", "Verein", "Stiftung"
        ]
        
        # Swiss legal forms
        self.swiss_legal_forms = [
            "AG", "GmbH", "Einzelfirma", "Kollektivgesellschaft", 
            "Kommanditgesellschaft", "Genossenschaft", "Verein", "Stiftung"
        ]
        
    def run(
        self,
        case_input: Dict[str, Any],
        meta_case_normalized: Dict[str, Any],
        meta_target_entity_stub: Dict[str, Any],
        registry_snapshot: Optional[Dict[str, Any]] = None,
    ) -> AgentResult:
        """
        Execute DACH legal identity extraction.
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
            # Extract legal identity from Austrian/Swiss sources
            legal_data = self._extract_dach_legal_identity(company_name, domain)
            
            if legal_data and legal_data["country_code"] in ["AT", "CH"]:
                # Update entity with DACH legal information
                entity_update = {
                    "entity_key": meta_target_entity_stub.get("entity_key", ""),
                    "entity_type": "target_company",
                    "entity_name": legal_data["legal_name"],
                    "legal_name": legal_data["legal_name"],
                    "legal_form": legal_data["legal_form"],
                    "domain": case_input.get("web_domain", "n/v"),
                    "industry": case_input.get("industry", "n/v"),
                    "street_name": legal_data["street_name"],
                    "house_number": legal_data["house_number"],
                    "postal_code": legal_data["postal_code"],
                    "city": legal_data["city"],
                    "state": legal_data["state"],
                    "country": legal_data["country"],
                    "country_code": legal_data["country_code"]
                }
                
                output["entities_delta"] = [entity_update]
                output["findings"] = [legal_data["findings"]]
                output["sources"] = legal_data["sources"]
                
        except Exception as e:
            self.logger.error(f"Error in AG-10.1 execution: {str(e)}")
            output["findings"] = [{
                "error": f"DACH legal identity extraction failed: {str(e)}",
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
        
    def _extract_dach_legal_identity(self, company_name: str, domain: str) -> Optional[Dict[str, Any]]:
        """
        Extract DACH legal identity using OpenAI with Austrian/Swiss focus.
        """
        api_key = os.getenv("OPEN-AI-KEY") or os.getenv("OPENAI_API_KEY")
        if not api_key:
            return self._fallback_dach_data(company_name)
            
        # Build DACH-specific search context
        search_context = f"""
Company: {company_name}
Domain: {domain}

Extract Austrian or Swiss legal identity information from the company's Impressum/legal notice.
Focus on DACH region legal requirements and address formats.

IMPORTANT: Always search for the COMPLETE legal company name, even if the input already contains a legal form.
For example: "Company AG" might actually be "Company AG & Co. KG" - find the full name.

Find:
1. Complete legal company name (including ALL legal forms)
2. Legal form (Austria: GmbH, AG, e.U., OG, KG / Switzerland: AG, GmbH, Einzelfirma)
3. Address: Street name, house number (may include /Top/Tür for Austria), 4-digit postal code, city, state/canton
4. Country (Austria/Österreich or Switzerland/Schweiz)
5. Only extract information from official company website/Impressum
"""
        
        try:
            response_format = {
                "type": "json_schema",
                "json_schema": {
                    "name": "dach_legal_identity",
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
                        "content": "Extract Austrian or Swiss legal identity information. ALWAYS find the complete legal company name, even if the input already contains a legal form. Use 'n/v' only if information is unavailable. Country codes: AT for Austria, CH for Switzerland. Focus on DACH legal forms and 4-digit postal codes."
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
                    return self._process_dach_results(legal_data, company_name)
                except json.JSONDecodeError:
                    pass
                    
        except Exception as e:
            self.logger.error(f"OpenAI DACH legal extraction failed: {str(e)}")
            
        return self._fallback_dach_data(company_name)
        
    def _process_dach_results(self, legal_data: Dict[str, Any], company_name: str) -> Dict[str, Any]:
        """Process and validate DACH legal extraction results."""
        accessed_at = datetime.now(timezone.utc).isoformat()
        
        # Validate country code
        country_code = legal_data.get("country_code", "").upper()
        if country_code not in ["AT", "CH"]:
            return None  # Not DACH region
            
        # Extract and validate legal form
        legal_name = legal_data.get("legal_name", "n/v")
        legal_form = self._extract_dach_legal_form(legal_name, country_code)
        
        # Validate 4-digit postal code for AT/CH
        postal_code = legal_data.get("postal_code", "n/v")
        if postal_code != "n/v" and not re.match(r"^\d{4}$", postal_code):
            postal_code = "n/v"
            
        # Validate house number format (including Austrian /Top/Tür)
        house_number = legal_data.get("house_number", "n/v")
        if house_number != "n/v" and not re.match(r"^\d+[a-zA-Z]?(/\d+)?(-\d+)?$", house_number):
            house_number = "n/v"
            
        country = "Austria" if country_code == "AT" else "Switzerland"
        
        findings = {
            "legal_name": legal_name,
            "legal_form": legal_form,
            "street_name": legal_data.get("street_name", "n/v"),
            "house_number": house_number,
            "postal_code": postal_code,
            "city": legal_data.get("city", "n/v"),
            "state": legal_data.get("state", "n/v"),
            "country": country,
            "country_code": country_code,
            "country_detected": country_code
        }
        
        sources = [{
            "publisher": f"{company_name} Impressum",
            "url": f"https://{company_name.lower().replace(' ', '')}.com/impressum",
            "title": f"DACH legal identity research for {company_name}",
            "accessed_at_utc": accessed_at
        }]
        
        return {
            **findings,
            "findings": findings,
            "sources": sources
        }
        
    def _extract_dach_legal_form(self, legal_name: str, country_code: str) -> str:
        """Extract legal form from company name based on country."""
        if legal_name == "n/v":
            return "n/v"
            
        legal_forms = self.austrian_legal_forms if country_code == "AT" else self.swiss_legal_forms
        
        # Check for exact matches
        for form in legal_forms:
            if form in legal_name:
                return form
                
        # Extract from end of name
        words = legal_name.split()
        if len(words) >= 2:
            potential_form = " ".join(words[-2:])
            for form in legal_forms:
                if form.lower() in potential_form.lower():
                    return form
                    
        return "n/v"
        
    def _fallback_dach_data(self, company_name: str) -> Dict[str, Any]:
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
            "title": f"Fallback DACH legal data for {company_name}",
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
Agent = AG10_1_IdentityLegalDACH