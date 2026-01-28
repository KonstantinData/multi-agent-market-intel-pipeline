"""
AG-13.1 Financial Indicators Firmographics Agent

Extracts financial metrics indicating company size and purchasing power.
"""

import os
import json
from datetime import datetime, timezone
from typing import Dict, Any, Optional

import httpx

from ...common.base_agent import BaseAgent, AgentResult


class AG13_1_FinancialIndicatorsAgent(BaseAgent):
    """
    Agent for extracting financial firmographics.
    
    Extracts:
    - Revenue (last fiscal year)
    - Revenue trend (YoY)
    - EBIT/EBITDA (investment capacity)
    - Balance sheet total / equity ratio
    """

    def __init__(self):
        super().__init__()
        self.agent_id = "AG-13.1"
        self.agent_name = "ag13_1_financial_indicators"
        self.api_key = os.getenv("OPEN-AI-KEY") or os.getenv("OPENAI_API_KEY")

    def run(
        self,
        case_input: Dict[str, Any],
        meta_case_normalized: Dict[str, Any],
        meta_target_entity_stub: Dict[str, Any],
        registry_snapshot: Optional[Dict[str, Any]] = None,
    ) -> AgentResult:
        """Execute financial indicators research."""
        
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

        financial_data = self._research_financials(company_name, domain)
        
        entity_update = {
            "entity_key": meta_target_entity_stub.get("entity_key", ""),
            "entity_type": "target_company",
            "firmographics_financial": financial_data
        }
        
        output["entities_delta"] = [entity_update]
        output["findings"] = [financial_data]
        output["sources"] = [{
            "publisher": "Financial Research",
            "url": f"https://{domain}",
            "title": f"Financial analysis for {company_name}",
            "accessed_at_utc": datetime.now(timezone.utc).isoformat()
        }]

        return AgentResult(ok=True, output=output)

    def _research_financials(self, company_name: str, domain: str) -> Dict[str, Any]:
        """Research financial indicators using LLM."""
        
        prompt = f"""Research financial indicators for {company_name} ({domain}).

Extract:
1. Revenue last fiscal year (in EUR or USD)
2. Revenue trend YoY (growth/decline %)
3. EBIT or EBITDA (if available)
4. Balance sheet total
5. Equity ratio

Use "n/v" if not available."""

        try:
            response_format = {
                "type": "json_schema",
                "json_schema": {
                    "name": "financial_data",
                    "strict": True,
                    "schema": {
                        "type": "object",
                        "properties": {
                            "revenue_last_fy": {"type": "string"},
                            "revenue_trend_yoy": {"type": "string"},
                            "ebit_ebitda": {"type": "string"},
                            "balance_sheet_total": {"type": "string"},
                            "equity_ratio": {"type": "string"}
                        },
                        "required": ["revenue_last_fy", "revenue_trend_yoy", "ebit_ebitda", "balance_sheet_total", "equity_ratio"],
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
            "revenue_last_fy": "n/v",
            "revenue_trend_yoy": "n/v",
            "ebit_ebitda": "n/v",
            "balance_sheet_total": "n/v",
            "equity_ratio": "n/v"
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


Agent = AG13_1_FinancialIndicatorsAgent
