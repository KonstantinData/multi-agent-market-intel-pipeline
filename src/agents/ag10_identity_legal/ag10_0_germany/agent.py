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
from typing import Dict, Any, Optional

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

        # German legal forms for extraction (including compound forms)
        self.german_legal_forms = [
            "SE & Co. KGaA", "GmbH & Co. KG", "AG & Co. KGaA", "SE & Co. KG",
            "GmbH", "UG (haftungsbeschränkt)", "UG", "AG", "SE", "KGaA",
            "KG", "OHG", "e.K.", "GbR", "e.V.", "Stiftung"
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
                    "legal_name": legal_data["legal_name"],
                    "legal_form": legal_data["legal_form"],
                    "domain": case_input.get("web_domain", "n/v"),
                    "industry": case_input.get("industry", "n/v"),
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

IMPORTANT: Always search for the COMPLETE legal company name, even if the input already contains a legal form.
For example: "IMS Gear SE" might actually be "IMS Gear SE & Co. KGaA" - find the full name.

Find:
1. Complete legal company name (including ALL legal forms like GmbH, AG, SE & Co. KGaA, etc.)
2. Legal form (GmbH, UG, AG, SE, KGaA, SE & Co. KGaA, etc.)
3. German address: Street name, house number, PLZ (5-digit), city, state
4. Only extract information that appears on the company's official website/Impressum
"""

        try:
            # First try to fetch actual website content
            website_content = self._fetch_website_content(domain)

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

            # Include actual website content in the prompt
            content_prompt = f"""
Website Content from {domain}:
{website_content[:4000]}

Extract the following from the Impressum section above:
1. Complete legal company name (e.g., "IMS Gear SE & Co. KGaA")
2. Legal form (e.g., "SE & Co. KGaA", "GmbH", "AG")
3. Street name (e.g., "Heinrich-Hertz-Str.")
4. House number (e.g., "16")
5. PLZ - 5-digit postal code (e.g., "78166")
6. City (e.g., "Donaueschingen")
7. State/Bundesland (e.g., "Baden-Württemberg")

If a field is not found, use 'n/v'.
"""

            payload = {
                "model": "gpt-4o",
                "messages": [
                    {
                        "role": "system",
                        "content": "You are a data extraction system for German Impressum pages. "
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
                    return self._process_german_results(legal_data, company_name, domain)
                except json.JSONDecodeError:
                    pass

        except Exception as e:
            pass

        return self._fallback_german_data(company_name)

    def _process_german_results(self, legal_data: Dict[str, Any], company_name: str, domain: str) -> Dict[str, Any]:
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
            "publisher": f"{legal_name} Impressum",
            "url": f"https://www.{domain}/impressum",
            "title": f"German legal identity research for {legal_name}",
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

    def _fetch_website_content(self, domain: str) -> str:
        """Fetch actual website content from impressum/legal pages."""
        # Try www first, then without
        domain_variants = []
        if not domain.startswith('www.'):
            domain_variants.append(f'www.{domain}')
        domain_variants.append(domain)

        # German Impressum-specific URL patterns (legally required pages)
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
                            import re
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
                except Exception as e:
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
Agent = AG10_0_IdentityLegalGermany