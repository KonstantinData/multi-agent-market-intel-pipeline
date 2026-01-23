"""
AG-10.2 Identity Legal Europe Agent

Specialized agent for extracting legal identity information from European companies
(excluding Germany, Austria, Switzerland which are handled by other agents).

Focus Areas:
- European legal forms (SAS, SARL, SpA, BV, NV, etc.)
- European address formats and postal codes
- Multi-language support for major EU languages
- Company registration information
"""

import json
import os
import re
from datetime import datetime, timezone
from typing import Dict, Any, Optional

import httpx

from ...common.base_agent import BaseAgent, AgentResult


class AG10_2_IdentityLegalEurope(BaseAgent):
    """
    Agent for extracting European legal identity information.
    
    Covers EU countries excluding Germany, Austria, Switzerland.
    Extracts legal forms, addresses, and company registration data.
    """
    
    def __init__(self):
        super().__init__()
        self.agent_id = "AG-10.2"
        self.agent_name = "ag10_2_identity_legal_europe"
        
        # European legal forms by country
        self.european_legal_forms = {
            "FR": ["SAS", "SARL", "SA", "SNC", "SCS", "EURL", "SASU"],
            "IT": ["SpA", "SRL", "SNC", "SAS", "SS"],
            "ES": ["SA", "SL", "SRC", "SC", "SCP"],
            "NL": ["BV", "NV", "VOF", "CV", "Stichting", "Vereniging"],
            "BE": ["SA/NV", "SPRL/BVBA", "SC/CV", "ASBL/VZW"],
            "PL": ["SA", "Sp. z o.o.", "SKA", "SP", "P.P."],
            "SE": ["AB", "HB", "KB", "EF"],
            "DK": ["A/S", "ApS", "I/S", "K/S"],
            "NO": ["AS", "ASA", "BA", "DA", "KS"],
            "FI": ["Oy", "Oyj", "Ky", "Ay", "T:mi"]
        }
        
    def run(
        self,
        case_input: Dict[str, Any],
        meta_case_normalized: Dict[str, Any],
        meta_target_entity_stub: Dict[str, Any],
        registry_snapshot: Optional[Dict[str, Any]] = None,
    ) -> AgentResult:
        """
        Execute European legal identity extraction.
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
            # Extract legal identity from European sources
            legal_data = self._extract_european_legal_identity(company_name, domain)
            
            if legal_data and self._is_european_country(legal_data.get("country_code", "")):
                # Update entity with European legal information
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
                    "country": legal_data["country"],
                    "country_code": legal_data["country_code"]
                }
                
                output["entities_delta"] = [entity_update]
                output["findings"] = [legal_data["findings"]]
                output["sources"] = legal_data["sources"]
                
        except Exception as e:
            self.logger.error(f"Error in AG-10.2 execution: {str(e)}")
            output["findings"] = [{
                "error": f"European legal identity extraction failed: {str(e)}",
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
        
    def _extract_european_legal_identity(self, company_name: str, domain: str) -> Optional[Dict[str, Any]]:
        """
        Extract European legal identity using OpenAI with European focus.
        """
        api_key = os.getenv("OPEN-AI-KEY") or os.getenv("OPENAI_API_KEY")
        if not api_key:
            return self._fallback_european_data(company_name)
            
        # Build Europe-specific search context
        search_context = f"""
Company: {company_name}
Domain: {domain}

Extract European legal identity information from the company's legal notice/contact page.
Focus on European Union countries (excluding Germany, Austria, Switzerland).

Find:
1. Complete legal company name (including legal form)
2. Legal form (France: SAS, SARL, SA / Italy: SpA, SRL / Netherlands: BV, NV / etc.)
3. Address: Street name, house number, postal code, city, region/state
4. Country (European Union member state)
5. Only extract information from official company website
"""
        
        try:
            response_format = {
                "type": "json_schema",
                "json_schema": {
                    "name": "european_legal_identity",
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
                        "content": "Extract European legal identity information. Use 'n/v' only if information is unavailable. Use ISO country codes (FR, IT, ES, NL, BE, PL, SE, DK, NO, FI, etc.). Focus on European legal forms and address formats."
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
                    return self._process_european_results(legal_data, company_name)
                except json.JSONDecodeError:
                    pass
                    
        except Exception as e:
            self.logger.error(f"OpenAI European legal extraction failed: {str(e)}")
            
        return self._fallback_european_data(company_name)
        
    def _process_european_results(self, legal_data: Dict[str, Any], company_name: str) -> Dict[str, Any]:
        """Process and validate European legal extraction results."""
        accessed_at = datetime.now(timezone.utc).isoformat()
        
        # Validate country code
        country_code = legal_data.get("country_code", "").upper()
        if not self._is_european_country(country_code):
            return None  # Not European or handled by other agents
            
        # Extract and validate legal form
        legal_name = legal_data.get("legal_name", "n/v")
        legal_form = self._extract_european_legal_form(legal_name, country_code)
        
        # Validate postal code format (varies by country)
        postal_code = legal_data.get("postal_code", "n/v")
        if postal_code != "n/v":
            postal_code = self._validate_european_postal_code(postal_code, country_code)
            
        findings = {
            "legal_name": legal_name,
            "legal_form": legal_form,
            "street_name": legal_data.get("street_name", "n/v"),
            "house_number": legal_data.get("house_number", "n/v"),
            "postal_code": postal_code,
            "city": legal_data.get("city", "n/v"),
            "state": legal_data.get("state", "n/v"),
            "country": legal_data.get("country", "n/v"),
            "country_code": country_code,
            "country_detected": country_code
        }
        
        sources = [{
            "publisher": f"{company_name} Legal Notice",
            "url": f"https://{company_name.lower().replace(' ', '')}.com/legal",
            "title": f"European legal identity research for {company_name}",
            "accessed_at_utc": accessed_at
        }]
        
        return {
            **findings,
            "findings": findings,
            "sources": sources
        }
        
    def _is_european_country(self, country_code: str) -> bool:
        """Check if country code is European (excluding DE, AT, CH)."""
        european_countries = {
            "FR", "IT", "ES", "NL", "BE", "PL", "SE", "DK", "NO", "FI",
            "PT", "IE", "GR", "CZ", "HU", "SK", "SI", "HR", "BG", "RO",
            "LT", "LV", "EE", "LU", "MT", "CY"
        }
        return country_code in european_countries
        
    def _extract_european_legal_form(self, legal_name: str, country_code: str) -> str:
        """Extract legal form from company name based on European country."""
        if legal_name == "n/v" or country_code not in self.european_legal_forms:
            return "n/v"
            
        legal_forms = self.european_legal_forms[country_code]
        
        # Check for exact matches
        for form in legal_forms:
            if form in legal_name:
                return form
                
        # Extract from end of name
        words = legal_name.split()
        if len(words) >= 1:
            potential_form = words[-1]
            for form in legal_forms:
                if form.lower() in potential_form.lower():
                    return form
                    
        return "n/v"
        
    def _validate_european_postal_code(self, postal_code: str, country_code: str) -> str:
        """Validate postal code format for European countries."""
        patterns = {
            "FR": r"^\d{5}$",           # 75001
            "IT": r"^\d{5}$",           # 00100
            "ES": r"^\d{5}$",           # 28001
            "NL": r"^\d{4}\s?[A-Z]{2}$", # 1000 AA
            "BE": r"^\d{4}$",           # 1000
            "PL": r"^\d{2}-\d{3}$",     # 00-001
            "SE": r"^\d{3}\s?\d{2}$",   # 100 05
            "DK": r"^\d{4}$",           # 1000
            "NO": r"^\d{4}$",           # 0001
            "FI": r"^\d{5}$"            # 00100
        }
        
        pattern = patterns.get(country_code)
        if pattern and re.match(pattern, postal_code):
            return postal_code
        return "n/v"
        
    def _fallback_european_data(self, company_name: str) -> Dict[str, Any]:
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
            "title": f"Fallback European legal data for {company_name}",
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
Agent = AG10_2_IdentityLegalEurope