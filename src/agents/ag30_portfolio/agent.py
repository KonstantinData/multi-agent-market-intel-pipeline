"""
    DESCRIPTION
    -----------
    AG-30 baseline agent implementation.
This agent is contract-compliant and deterministic.
It reads the cumulative registry snapshot (if provided) and may emit n/v findings.
    """

from __future__ import annotations

from typing import Any, Dict, Optional

from src.agents.common.baseline_agent import BaselineAgent
from src.agents.common.base_agent import AgentResult


#note: Concrete agent class for AG-30 (ag30_portfolio).
class Agent(BaselineAgent):
    """
    #note: Purpose: Products/services portfolio overview and key offerings.
    """

    step_id = "AG-30"
    agent_name = "ag30_portfolio"
    baseline_purpose = "Products/services portfolio overview and key offerings."


#note: Explicit module-level alias used by the step registry.
AgentClass = Agent
