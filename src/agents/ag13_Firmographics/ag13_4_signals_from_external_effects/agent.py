"""
AG-13.4 External Signals Firmographics Agent

Extracts signals from external presence and activities.
"""

import os
import json
from datetime import datetime, timezone
from typing import Dict, Any, Optional

import httpx

from ...common.base_agent import BaseAgent, AgentResult


class AG13_4_ExternalSignalsAgent(BaseAgent):
    """Agent for extracting external signals firmographics."""

    def __init__(self):
        super().__init__()
        self.agent_id = "AG-13.4"
        self.agent_name = "ag13_4_signals_from_external_effects"
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

        external_data = self._research_external_signals(company_name, domain)
        
        entity_update = {
            "entity_key": meta_target_entity_stub.get("entity_key", ""),
            "entity_type": "target_company",
            "firmographics_external": external_data
        }
        
        output["entities_delta"] = [entity_update]
        output["findings"] = [external_data]
        output["sources"] = [{
            "publisher": "External Signals Research",
            "url": f"https://{domain}",
            "title": f"External signals analysis for {company_name}",
            "accessed_at_utc": datetime.now(timezone.utc).isoformat()
        }]

        return AgentResult(ok=True, output=output)

    def _research_external_signals(self, company_name: str, domain: str) -> Dict[str, Any]:
        prompt = f"""Research external signals for {company_name} ({domain}).

Extract:
1. LinkedIn company size range
2. Career page / open positions (hiring intensity)
3. Press mentions / investments / funding / M&A activities
4. Growth signals from public sources

Use "n/v" if not available."""

        try:
            response_format = {
                "type": "json_schema",
                "json_schema": {
                    "name": "external_data",
                    "strict": True,
                    "schema": {
                        "type": "object",
                        "properties": {
                            "linkedin_size_range": {"type": "string"},
                            "open_positions": {"type": "string"},
                            "press_funding_ma": {"type": "string"},
                            "growth_signals": {"type": "string"}
                        },
                        "required": ["linkedin_size_range", "open_positions", "press_funding_ma", "growth_signals"],
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
            "linkedin_size_range": "n/v",
            "open_positions": "n/v",
            "press_funding_ma": "n/v",
            "growth_signals": "n/v"
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


Agent = AG13_4_ExternalSignalsAgent
