"""
AG-13.5 Buying Power Firmographics Agent

Extracts buying power and decision-making structure indicators.
"""

import os
import json
from datetime import datetime, timezone
from typing import Dict, Any, Optional

import httpx

from ...common.base_agent import BaseAgent, AgentResult


class AG13_5_BuyingPowerAgent(BaseAgent):
    """Agent for extracting buying power firmographics."""

    def __init__(self):
        super().__init__()
        self.agent_id = "AG-13.5"
        self.agent_name = "ag13_5_buying_power"
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

        buying_power_data = self._research_buying_power(company_name, domain)
        
        entity_update = {
            "entity_key": meta_target_entity_stub.get("entity_key", ""),
            "entity_type": "target_company",
            "firmographics_buying_power": buying_power_data
        }
        
        output["entities_delta"] = [entity_update]
        output["findings"] = [buying_power_data]
        output["sources"] = [{
            "publisher": "Buying Power Research",
            "url": f"https://{domain}",
            "title": f"Buying power analysis for {company_name}",
            "accessed_at_utc": datetime.now(timezone.utc).isoformat()
        }]

        return AgentResult(ok=True, output=output)

    def _research_buying_power(self, company_name: str, domain: str) -> Dict[str, Any]:
        prompt = f"""Research buying power and decision-making structure for {company_name} ({domain}).

Extract:
1. Budget ownership structure (who can approve purchases)
2. Procurement setup (centralized/decentralized)
3. Decision-making paths (founder-led vs. management/board)
4. Typical approval thresholds

Use "n/v" if not available."""

        try:
            response_format = {
                "type": "json_schema",
                "json_schema": {
                    "name": "buying_power_data",
                    "strict": True,
                    "schema": {
                        "type": "object",
                        "properties": {
                            "budget_ownership": {"type": "string"},
                            "procurement_setup": {"type": "string"},
                            "decision_paths": {"type": "string"},
                            "approval_thresholds": {"type": "string"}
                        },
                        "required": ["budget_ownership", "procurement_setup", "decision_paths", "approval_thresholds"],
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
            "budget_ownership": "n/v",
            "procurement_setup": "n/v",
            "decision_paths": "n/v",
            "approval_thresholds": "n/v"
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


Agent = AG13_5_BuyingPowerAgent
