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
            "findings": {},
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
                
                output["findings"] = financial_data["findings"]
                output["sources"] = financial_data["sources"]
            
        except Exception as e:
            self.logger.error(f"Error in AG-21 execution: {str(e)}")
            output["findings"] = {"error": f"Financial research failed: {str(e)}"}
        
        # Ensure required fields for contract validation
        if not output["findings"]:
            output["findings"] = {
                "currency": "n/v",
                "time_series": [],
                "trend_summary": "n/v"
            }
        
        return AgentResult(ok=True, output=output)
    
    def _research_financial_metrics(self, company_name: str, domain: str) -> Optional[Dict[str, Any]]:
        """
        Research financial metrics for the target company.
        
        Args:
            company_name: Company name
            domain: Company domain
            
        Returns:
            Financial data structure or None if not found
        """
        # Search queries for different financial metrics
        search_queries = [
            f"{company_name} annual revenue last 4 years",
            f"{company_name} EBITDA last 3 years",
            f"{company_name} equity ratio 2024",
            f"{company_name} investments last 3 years",
            f"{company_name} financial statements",
            f"{company_name} investor relations"
        ]
        
        sources = []
        financial_profile = {
            "revenue_data": "n/v",
            "ebitda_data": "n/v", 
            "equity_ratio": "n/v",
            "capex_data": "n/v",
            "currency": "n/v"
        }
        
        findings = {
            "currency": "n/v",
            "time_series": [],
            "equity_ratio_2024": "n/v",
            "trend_summary": "n/v"
        }
        
        # Simulate financial data collection
        # In real implementation, this would use ChatGPT Search or other APIs
        for query in search_queries:
            # Placeholder for actual search implementation
            source_url = f"https://example-financial-source.com/search?q={query.replace(' ', '+')}"
            sources.append({
                "publisher": "Financial Research Database",
                "url": source_url,
                "title": f"Financial data for {company_name}",
                "accessed_at_utc": datetime.now(timezone.utc).isoformat()
            })
        
        # Example financial data structure (would be populated from actual research)
        if company_name and domain:
            findings = {
                "currency": "EUR",
                "time_series": [
                    {"year": 2022, "revenue": "n/v", "ebitda": "n/v", "net_debt": "n/v", "capex": "n/v"},
                    {"year": 2023, "revenue": "n/v", "ebitda": "n/v", "net_debt": "n/v", "capex": "n/v"},
                    {"year": 2024, "revenue": "n/v", "ebitda": "n/v", "net_debt": "n/v", "capex": "n/v"}
                ],
                "equity_ratio_2024": "n/v",
                "trend_summary": "Financial data requires verification from official sources."
            }
            
            financial_profile = {
                "revenue_trend": "n/v",
                "profitability_trend": "n/v",
                "leverage_trend": "n/v",
                "investment_pattern": "n/v",
                "working_capital_pressure": "n/v"
            }
        
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