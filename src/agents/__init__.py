"""
Agent package metadata.

This module provides lightweight, human-readable descriptors for agents that
are useful for discovery and documentation.
"""

AGENT_INFO = {
    "AG-21": {
        "agent_name": "ag21_financial_development",
        "module_path": "src.agents.ag21_financial_developmet.agent",
        "purpose": "Collect historical financial KPIs (Revenue, EBITDA, Net Debt, CAPEX) with sources or n/v.",
    },
}

__all__ = ["AGENT_INFO"]
