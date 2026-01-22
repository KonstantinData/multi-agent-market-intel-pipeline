"""
    DESCRIPTION
    -----------
    AG-61 baseline agent implementation.
This agent is contract-compliant and deterministic.
It reads the cumulative registry snapshot (if provided) and may emit n/v findings.
    """

from __future__ import annotations


from src.agents.common.baseline_agent import BaselineAgent


#note: Concrete agent class for AG-61 (ag61_surplus_stock_signals).
class Agent(BaselineAgent):
    """
    #note: Purpose: Surplus stock / liquidation signals.
    """

    step_id = "AG-61"
    agent_name = "ag61_surplus_stock_signals"
    baseline_purpose = "Surplus stock / liquidation signals."


#note: Explicit module-level alias used by the step registry.
AgentClass = Agent
