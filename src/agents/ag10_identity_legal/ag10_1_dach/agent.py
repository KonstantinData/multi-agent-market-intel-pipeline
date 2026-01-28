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
        
        # Austrian legal forms (including compound forms)
        self.austrian_legal_forms = [
            "GmbH & Co KG", "AG & Co KG", "GmbH", "AG", "e.U.", "OG", "KG",
            "Genossenschaft", "Verein", "Stiftung"
        ]
        
        # Swiss legal forms (including compound forms)
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
                    "street_name": legal_data["street_name"],
                    "house_number": legal_data["house_number"],
                    "postal_code": legal_data["postal_code"],
                    "city": legal_data["city"],
                    "state": legal_data["state"],
                    "phone_number": legal_data.get("phone_number", "n/v"),
                    "email": legal_data.get("email", "n/v"),
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
            
        try:
            # Fetch content only from impressum pages
            website_content = self._fetch_impressum_content(domain)
            
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
                            "country_code": {"type": "string"},
                            "phone_number": {"type": "string"},
                            "email": {"type": "string"}
                        },
                        "required": ["legal_name", "legal_form", "street_name", "house_number", "postal_code", "city", "state", "country", "country_code", "phone_number", "email"],
                        "additionalProperties": False
                    }
                }
            }
            
            # Include actual website content in the prompt
            content_prompt = f"""
Website Content from {domain}:
{website_content[:4000]}

Extract the following from the Impressum section above:
1. Complete legal company name (e.g., "Company AG", "Company GmbH & Co KG")
2. Legal form (Austria: GmbH, AG, e.U., OG, KG / Switzerland: AG, GmbH, etc.)
3. Street name (e.g., "Hauptstraße")
4. House number (e.g., "16" or "16/Top 5" for Austria)
5. 4-digit postal code (e.g., "1010" for Vienna, "8001" for Zurich)
6. City (e.g., "Wien", "Zürich")
7. State/Canton (e.g., "Wien", "Zürich")
8. Country (Austria/Österreich or Switzerland/Schweiz)
9. Country code (AT or CH)

If a field is not found, use 'n/v'.
"""
            
            payload = {
                "model": "gpt-4o",
                "messages": [
                    {
                        "role": "system",
                        "content": "You are a data extraction system for Austrian and Swiss Impressum pages. "
                        "Extract company information that is explicitly stated in the provided content. "
                        "If a field is clearly not present, use 'n/v'."
                    },
                    {
                        "role": "user",
                        "content": content_prompt
                    }
                ],
                "temperature": 0.0,
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
                    return self._process_dach_results(legal_data, company_name, domain)
                except json.JSONDecodeError:
                    pass
                    
        except Exception as e:
            self.logger.error(f"OpenAI DACH legal extraction failed: {str(e)}")
            
        return self._fallback_dach_data(company_name)
        
    def _process_dach_results(self, legal_data: Dict[str, Any], company_name: str, domain: str = "") -> Dict[str, Any]:
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
            "country_detected": country_code,
            "phone_number": legal_data.get("phone_number", "n/v"),
            "email": legal_data.get("email", "n/v")
        }
        
        sources = [{
            "publisher": f"{legal_name} Impressum",
            "url": f"https://www.{domain}/impressum",
            "title": f"DACH legal identity research for {legal_name}",
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
            "country_detected": "n/v",
            "phone_number": "n/v",
            "email": "n/v"
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
        
    def _fetch_impressum_content(self, domain: str) -> str:
        """Fetch actual website content from impressum/legal pages."""
        # Try www first, then without
        domain_variants = []
        if not domain.startswith('www.'):
            domain_variants.append(f'www.{domain}')
        domain_variants.append(domain)

        # DACH Impressum-specific URL patterns
        url_patterns = [
            '/impressum',
            '/de/impressum',
            '/unternehmen/impressum',
            '/footer/impressum',
            '/imprint',
            '/de/imprint',
            '/legal-notice',
            '/rechtliches/impressum',
            '/info/impressum'
        ]

        content = ""
        
        for domain_var in domain_variants:
            for pattern in url_patterns:
                url = f"https://{domain_var}{pattern}"
                try:
                    with httpx.Client(timeout=10.0, follow_redirects=True) as client:
                        resp = client.get(url)
                        if resp.status_code == 200:
                            # Extract text from HTML
                            html_content = resp.text
                            
                            # Simple HTML tag removal
                            import html
                            text = re.sub(r'<script[^>]*>.*?</script>', '', html_content, flags=re.DOTALL)
                            text = re.sub(r'<style[^>]*>.*?</style>', '', text, flags=re.DOTALL)
                            text = re.sub(r'<[^>]+>', ' ', text)
                            text = html.unescape(text)  # Decode HTML entities like &amp;
                            text = re.sub(r'\s+', ' ', text)
                            
                            content += f"\n\n--- Content from {url} ---\n"
                            content += text[:6000]
                            if len(content) > 10000:
                                return content
                except Exception:
                    continue

        if not content:
            return "No website content available"
        
        return content
        
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