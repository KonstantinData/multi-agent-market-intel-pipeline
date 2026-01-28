"""
AG-13.3 Operational Complexity Firmographics Agent

Extracts operational complexity indicators.
"""

import os
import json
from datetime import datetime, timezone
from typing import Dict, Any, Optional

import httpx

from ...common.base_agent import BaseAgent, AgentResult


class AG13_3_OperationalComplexityAgent(BaseAgent):
    """Agent for extracting operational complexity firmographics."""

    def __init__(self):
        super().__init__()
        self.agent_id = "AG-13.3"
        self.agent_name = "ag13_3_operational_complexity"
        self.api_key = os.getenv("OPEN-AI-KEY") or os.getenv("OPENAI_API_KEY")

    def run(
        self,
        case_input: Dict[str, Any],
        meta_case_normalized: Dict[str, Any],
        meta_target_entity_stub: Dict[str, Any],
        registry_snapshot: Optional[Dict[str, Any]] = None,
    ) -> AgentResult:
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

        operational_data = self._research_operational_complexity(company_name, domain)
        
        entity_update = {
            "entity_key": meta_target_entity_stub.get("entity_key", ""),
            "entity_type": "target_company",
            "firmographics_operational": operational_data
        }
        
        output["entities_delta"] = [entity_update]
        output["findings"] = [operational_data]
        output["sources"] = [{
            "publisher": "Operational Research",
            "url": f"https://{domain}",
            "title": f"Operational analysis for {company_name}",
            "accessed_at_utc": datetime.now(timezone.utc).isoformat()
        }]

        return AgentResult(ok=True, output=output)

    def _research_operational_complexity(self, company_name: str, domain: str) -> Dict[str, Any]:
        prompt = f"""Research operational complexity for {company_name} ({domain}).

Extract:
1. Number of legal entities/subsidiaries
2. Transaction volume indicators (orders, invoices, deliveries)
3. Supply chain/production presence (plants, warehouses, fulfillment)
4. IT/Tool landscape (ERP/CRM/HRIS systems, integration level)

Use "n/v" if not available."""

        try:
            response_format = {
                "type": "json_schema",
                "json_schema": {
                    "name": "operational_data",
                    "strict": True,
                    "schema": {
                        "type": "object",
                        "properties": {
                            "legal_entities": {"type": "string"},
                            "transaction_volume": {"type": "string"},
                            "supply_chain_presence": {"type": "string"},
                            "it_landscape": {"type": "string"}
                        },
                        "required": ["legal_entities", "transaction_volume", "supply_chain_presence", "it_landscape"],
                        "additionalProperties": False
                    }
                }
            }
            
            payload = {
                "model": "gpt-4o",
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.0,
                "max_tokens": 600,
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
            "legal_entities": "n/v",
            "transaction_volume": "n/v",
            "supply_chain_presence": "n/v",
            "it_landscape": "n/v"
        }

    def _create_step_meta(self) -> Dict[str, Any]:
        now = datetime.now(timezone.utc)
        return {
            "step_id": self.agent_id,
            "agent_name": self.agent_name,
            "run_id": getattr(self, 'run_id', 'unknown'),
            "started_at_utc": now.isoformat(),
            "finished_at_utc": now.isoformat(),
            "pipeline_version": "1.0.0"
        }


Agent = AG13_3_OperationalComplexityAgent
