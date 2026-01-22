"""
    DESCRIPTION
    -----------
    AG-21 baseline agent implementation.
This agent is contract-compliant and deterministic.
It reads the cumulative registry snapshot (if provided) and may emit n/v findings.
    """

from __future__ import annotations


from src.agents.common.baseline_agent import BaselineAgent


#note: Concrete agent class for AG-21 (ag21_financial_signals).
class Agent(BaselineAgent):
    """
    #note: Purpose: Financial / solvency signals and public risk indicators.
    """

    step_id = "AG-21"
    agent_name = "ag21_financial_signals"
    baseline_purpose = "Financial / solvency signals and public risk indicators."


# NOTE: Explicit module-level alias used by the step registry.
Agent = Agent21FinancialDevelopment
