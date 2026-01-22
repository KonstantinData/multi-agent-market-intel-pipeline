"""
    DESCRIPTION
    -----------
    AG-90 baseline agent implementation.
This agent is contract-compliant and deterministic.
It reads the cumulative registry snapshot (if provided) and may emit n/v findings.
    """

from __future__ import annotations


from src.agents.common.baseline_agent import BaselineAgent


#note: Concrete agent class for AG-90 (ag90_sales_playbook).
class Agent(BaselineAgent):
    """
    #note: Purpose: Sales playbook and CRM-ready output packaging.
    """

    step_id = "AG-90"
    agent_name = "ag90_sales_playbook"
    baseline_purpose = "Sales playbook and CRM-ready output packaging."


#note: Explicit module-level alias used by the step registry.
AgentClass = Agent
