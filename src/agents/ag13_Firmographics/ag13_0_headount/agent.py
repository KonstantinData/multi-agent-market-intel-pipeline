"""
AG-13.0 Headcount Firmographics Agent

Extracts headcount data - the most important practical indicator for company size.
"""

import os
import json
from datetime import datetime, timezone
from typing import Dict, Any, Optional

import httpx

from ...common.base_agent import BaseAgent, AgentResult


class AG13_0_HeadcountAgent(BaseAgent):
    """
    Agent for extracting headcount firmographics.
    
    Extracts:
    - Total employee count
    - Employees by location/country
    - Employees by function (Production, Sales, Engineering, IT)
    - Headcount growth trend (12-24 months)
    """

    def __init__(self):
        super().__init__()
        self.agent_id = "AG-13.0"
        self.agent_name = "ag13_0_headcount"
        self.api_key = os.getenv("OPEN-AI-KEY") or os.getenv("OPENAI_API_KEY")

    def run(
        self,
        case_input: Dict[str, Any],
        meta_case_normalized: Dict[str, Any],
        meta_target_entity_stub: Dict[str, Any],
        registry_snapshot: Optional[Dict[str, Any]] = None,
    ) -> AgentResult:
        """Execute headcount research."""
        
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
            output["findings"] = [{"error": "API key not configured"}]
            return AgentResult(ok=True, output=output)

        # Research headcount data
        headcount_data = self._research_headcount(company_name, domain)
        
        # Build entity update
        entity_update = {
            "entity_key": meta_target_entity_stub.get("entity_key", ""),
            "entity_type": "target_company",
            "firmographics_headcount": headcount_data
        }
        
        output["entities_delta"] = [entity_update]
        output["findings"] = [headcount_data]
        output["sources"] = [{
            "publisher": "Headcount Research",
            "url": f"https://{domain}",
            "title": f"Headcount analysis for {company_name}",
            "accessed_at_utc": datetime.now(timezone.utc).isoformat()
        }]

        return AgentResult(ok=True, output=output)

    def _research_headcount(self, company_name: str, domain: str) -> Dict[str, Any]:
        """Research headcount using LLM."""
        
        prompt = f"""Research and extract headcount information for {company_name} ({domain}).

Find:
1. Total employee count (current)
2. Employees by location/country (if available)
3. Employees by function: Production, Sales, Engineering, IT, Other
4. Headcount growth trend (last 12-24 months)

Provide realistic estimates based on company size, industry, and public information.
Use "n/v" if information is not available."""

        try:
            response_format = {
                "type": "json_schema",
                "json_schema": {
                    "name": "headcount_data",
                    "strict": True,
                    "schema": {
                        "type": "object",
                        "properties": {
                            "total_employees": {"type": "string"},
                            "employees_by_location": {"type": "string"},
                            "employees_production": {"type": "string"},
                            "employees_sales": {"type": "string"},
                            "employees_engineering": {"type": "string"},
                            "employees_it": {"type": "string"},
                            "employees_other": {"type": "string"},
                            "headcount_trend_12m": {"type": "string"}
                        },
                        "required": ["total_employees", "employees_by_location", "employees_production", "employees_sales", "employees_engineering", "employees_it", "employees_other", "headcount_trend_12m"],
                        "additionalProperties": False
                    }
                }
            }
            
            payload = {
                "model": "gpt-4o",
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.0,
                "max_tokens": 800,
                "response_format": response_format
            }
            
            headers = {"Authorization": f"Bearer {self.api_key}"}
            with httpx.Client(timeout=30.0) as client:
                resp = client.post("https://api.openai.com/v1/chat/completions", json=payload, headers=headers)
                resp.raise_for_status()
                data = resp.json()
            
            content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
            if content:
                return json.loads(content)
        except Exception:
            pass
        
        return {
            "total_employees": "n/v",
            "employees_by_location": "n/v",
            "employees_production": "n/v",
            "employees_sales": "n/v",
            "employees_engineering": "n/v",
            "employees_it": "n/v",
            "employees_other": "n/v",
            "headcount_trend_12m": "n/v"
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


Agent = AG13_0_HeadcountAgent
