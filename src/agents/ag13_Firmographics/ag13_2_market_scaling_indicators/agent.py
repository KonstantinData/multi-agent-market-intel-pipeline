"""
AG-13.2 Market & Scaling Indicators Firmographics Agent

Extracts market positioning and scaling indicators.
"""

import os
import json
from datetime import datetime, timezone
from typing import Dict, Any, Optional

import httpx

from ...common.base_agent import BaseAgent, AgentResult


class AG13_2_MarketScalingAgent(BaseAgent):
    """Agent for extracting market and scaling firmographics."""

    def __init__(self):
        super().__init__()
        self.agent_id = "AG-13.2"
        self.agent_name = "ag13_2_market_scaling_indicators"
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

        market_data = self._research_market_scaling(company_name, domain)
        
        entity_update = {
            "entity_key": meta_target_entity_stub.get("entity_key", ""),
            "entity_type": "target_company",
            "firmographics_market": market_data
        }
        
        output["entities_delta"] = [entity_update]
        output["findings"] = [market_data]
        output["sources"] = [{
            "publisher": "Market Research",
            "url": f"https://{domain}",
            "title": f"Market analysis for {company_name}",
            "accessed_at_utc": datetime.now(timezone.utc).isoformat()
        }]

        return AgentResult(ok=True, output=output)

    def _research_market_scaling(self, company_name: str, domain: str) -> Dict[str, Any]:
        prompt = f"""Research market and scaling indicators for {company_name} ({domain}).

Extract:
1. Industry sub-segment (SaaS, Manufacturing, Logistics, etc.)
2. Customer base type (B2B/B2C, number of customers, key accounts)
3. Regional coverage (DACH/EU/Global)
4. Product/Service portfolio complexity
5. Profitability or cash runway indicators

Use "n/v" if not available."""

        try:
            response_format = {
                "type": "json_schema",
                "json_schema": {
                    "name": "market_data",
                    "strict": True,
                    "schema": {
                        "type": "object",
                        "properties": {
                            "industry_segment": {"type": "string"},
                            "customer_base": {"type": "string"},
                            "regional_coverage": {"type": "string"},
                            "portfolio_complexity": {"type": "string"},
                            "profitability_indicators": {"type": "string"}
                        },
                        "required": ["industry_segment", "customer_base", "regional_coverage", "portfolio_complexity", "profitability_indicators"],
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
            "industry_segment": "n/v",
            "customer_base": "n/v",
            "regional_coverage": "n/v",
            "portfolio_complexity": "n/v",
            "profitability_indicators": "n/v"
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


Agent = AG13_2_MarketScalingAgent
