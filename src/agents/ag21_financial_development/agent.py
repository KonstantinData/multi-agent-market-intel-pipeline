"""
AG-21 Financial Development Agent

Specialized data harvester for financial stability and historical development
of target companies in Medical Technology, Mechanical Engineering, and Electrical Engineering sectors.
"""

from datetime import datetime, timezone
from typing import Dict, Any, Optional

from ..common.base_agent import BaseAgent, AgentResult


class AG21FinancialDevelopment(BaseAgent):
    """
    Agent responsible for collecting historical financial data to assess target companies for Liquisto.
    
    Key Metrics:
    - Revenue Growth (3-5 year period)
    - Profitability (EBITDA trends)
    - Capital Structure (equity ratio, net debt)
    - CAPEX (investment patterns)
    """
    
    def __init__(self):
        super().__init__()
        self.agent_id = "AG-21"
        self.agent_name = "ag21_financial_development"
    
    def run(
        self,
        case_input: Dict[str, Any],
        meta_case_normalized: Dict[str, Any],
        meta_target_entity_stub: Dict[str, Any],
        registry_snapshot: Optional[Dict[str, Any]] = None,
    ) -> AgentResult:
        """
        Execute financial development research for the target company.
        
        Args:
            case_input: Original case input
            meta_case_normalized: Normalized case input from AG-00
            meta_target_entity_stub: Target entity information from AG-00
            registry_snapshot: Current registry state
            
        Returns:
            AgentResult with financial development output
        """
        company_name = meta_case_normalized.get("company_name_canonical", "")
        domain = meta_case_normalized.get("web_domain_normalized", "")
        
        # Initialize output structure
        output = {
            "step_meta": self._create_step_meta(),
            "entities_delta": [],
            "relations_delta": [],
            "findings": [],
            "sources": []
        }
        
        try:
            # Perform financial research
            financial_data = self._research_financial_metrics(company_name, domain)
            
            # Update entities with financial information
            if financial_data:
                entity_update = {
                    "entity_key": meta_target_entity_stub.get("entity_key", ""),
                    "financial_profile": financial_data["profile"]
                }
                output["entities_delta"] = [entity_update]
                
                output["findings"] = [financial_data["findings"]]
                output["sources"] = financial_data["sources"]
            
        except Exception as e:
            self.logger.error(f"Error in AG-21 execution: {str(e)}")
            output["findings"] = [{"error": f"Financial research failed: {str(e)}", "currency": "n/v", "time_series": [], "trend_summary": "n/v"}]
        
        # Ensure required fields for contract validation
        if not output["findings"]:
            output["findings"] = [{
                "currency": "n/v",
                "time_series": [],
                "trend_summary": "n/v"
            }]
        
        return AgentResult(ok=True, output=output)
    
    def _research_financial_metrics(self, company_name: str, domain: str) -> Optional[Dict[str, Any]]:
        """
        Research financial metrics using OpenAI.
        """
        import os
        import httpx
        import json
        
        api_key = os.getenv("OPEN-AI-KEY") or os.getenv("OPENAI_API_KEY")
        if not api_key:
            return self._fallback_financial_data(company_name)
        
        financial_context = f"""
Company: {company_name}
Domain: {domain}

Find recent financial data for this company including:
- Annual revenue (last 3 years)
- EBITDA or profit margins
- Debt levels or equity ratio
- Capital expenditures
- Financial trends and outlook

Provide specific numbers where available, otherwise indicate 'n/v'.
"""
        
        try:
            # Define response schema for structured outputs
            response_format = {
                "type": "json_schema",
                "json_schema": {
                    "name": "financial_analysis",
                    "strict": True,
                    "schema": {
                        "type": "object",
                        "properties": {
                            "currency": {"type": "string"},
                            "revenue_trend": {"type": "string"},
                            "profitability_trend": {"type": "string"},
                            "leverage_trend": {"type": "string"},
                            "investment_pattern": {"type": "string"},
                            "working_capital_pressure": {"type": "string"},
                            "equity_ratio_2024": {"type": "string"},
                            "trend_summary": {"type": "string"},
                            "time_series": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "year": {"type": "integer"},
                                        "revenue": {"type": "string"},
                                        "ebitda": {"type": "string"},
                                        "net_debt": {"type": "string"},
                                        "capex": {"type": "string"}
                                    },
                                    "required": ["year", "revenue", "ebitda", "net_debt", "capex"],
                                    "additionalProperties": False
                                }
                            }
                        },
                        "required": ["currency", "revenue_trend", "profitability_trend", "leverage_trend", "investment_pattern", "working_capital_pressure", "equity_ratio_2024", "trend_summary", "time_series"],
                        "additionalProperties": False
                    }
                }
            }
            
            payload = {
                "model": "gpt-4o-mini",
                "messages": [
                    {
                        "role": "system",
                        "content": "Research and provide financial data for the given company. Use real data where possible, 'n/v' where not available. Provide structured financial analysis."
                    },
                    {
                        "role": "user",
                        "content": financial_context
                    }
                ],
                "temperature": 0.1,
                "max_tokens": 1000,
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
                    financial_data = json.loads(content)
                    return self._process_financial_results(financial_data, company_name)
                except json.JSONDecodeError:
                    pass
                    
        except Exception as e:
            self.logger.error(f"OpenAI financial research failed: {str(e)}")
        
        return self._fallback_financial_data(company_name)
    
    def _process_financial_results(self, financial_data: Dict[str, Any], company_name: str) -> Dict[str, Any]:
        """Process OpenAI financial research results."""
        accessed_at = datetime.now(timezone.utc).isoformat()
        
        # Extract financial profile
        financial_profile = {
            "revenue_trend": financial_data.get("revenue_trend", "n/v"),
            "profitability_trend": financial_data.get("profitability_trend", "n/v"),
            "leverage_trend": financial_data.get("leverage_trend", "n/v"),
            "investment_pattern": financial_data.get("investment_pattern", "n/v"),
            "working_capital_pressure": financial_data.get("working_capital_pressure", "n/v")
        }
        
        # Extract findings
        findings = {
            "currency": financial_data.get("currency", "EUR"),
            "time_series": financial_data.get("time_series", []),
            "equity_ratio_2024": financial_data.get("equity_ratio_2024", "n/v"),
            "trend_summary": financial_data.get("trend_summary", "AI-powered financial analysis completed")
        }
        
        # Ensure time_series has proper structure
        if not findings["time_series"]:
            findings["time_series"] = [
                {"year": 2022, "revenue": "n/v", "ebitda": "n/v", "net_debt": "n/v", "capex": "n/v"},
                {"year": 2023, "revenue": "n/v", "ebitda": "n/v", "net_debt": "n/v", "capex": "n/v"},
                {"year": 2024, "revenue": "n/v", "ebitda": "n/v", "net_debt": "n/v", "capex": "n/v"}
            ]
        
        sources = [{
            "publisher": "OpenAI Financial Research",
            "url": "https://api.openai.com/v1/chat/completions",
            "title": f"AI-powered financial research for {company_name}",
            "accessed_at_utc": accessed_at
        }]
        
        return {
            "profile": financial_profile,
            "findings": findings,
            "sources": sources
        }
    
    def _fallback_financial_data(self, company_name: str) -> Dict[str, Any]:
        """Fallback when OpenAI is not available."""
        financial_profile = {
            "revenue_trend": "n/v",
            "profitability_trend": "n/v",
            "leverage_trend": "n/v",
            "investment_pattern": "n/v",
            "working_capital_pressure": "n/v"
        }
        
        findings = {
            "currency": "EUR",
            "time_series": [
                {"year": 2022, "revenue": "n/v", "ebitda": "n/v", "net_debt": "n/v", "capex": "n/v"},
                {"year": 2023, "revenue": "n/v", "ebitda": "n/v", "net_debt": "n/v", "capex": "n/v"},
                {"year": 2024, "revenue": "n/v", "ebitda": "n/v", "net_debt": "n/v", "capex": "n/v"}
            ],
            "equity_ratio_2024": "n/v",
            "trend_summary": "Fallback data - OpenAI unavailable"
        }
        
        sources = [{
            "publisher": "Fallback Data",
            "url": "n/v",
            "title": f"Fallback financial data for {company_name}",
            "accessed_at_utc": datetime.now(timezone.utc).isoformat()
        }]
        
        return {
            "profile": financial_profile,
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


# NOTE: Wiring-safe alias for dynamic loaders expecting `Agent` symbol in this module.
Agent = AG21FinancialDevelopment