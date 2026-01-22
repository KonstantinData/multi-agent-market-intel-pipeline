"""
    DESCRIPTION
    -----------
    AG-50 baseline agent implementation.
This agent is contract-compliant and deterministic.
It reads the cumulative registry snapshot (if provided) and may emit n/v findings.
    """

from __future__ import annotations


from src.agents.common.baseline_agent import BaselineAgent


#note: Concrete agent class for AG-50 (ag50_projects_tenders).
class Agent(BaselineAgent):
    """
    #note: Purpose: Projects/tenders as demand or investment signals.
    """

    step_id = "AG-50"
    agent_name = "ag50_projects_tenders"
    baseline_purpose = "Projects/tenders as demand or investment signals."


#note: Explicit module-level alias used by the step registry.
AgentClass = Agent
